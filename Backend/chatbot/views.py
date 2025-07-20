import os
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from users.models import Chemical, Equipment, UserAccount


class ChatbotAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        query = request.data.get("query", "").strip()
        
        if not query:
            return Response({"detail": "No query provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Allow students to ask about safety with appropriate guidance
        query_lower = query.lower()
        
        # Check if it's an MSDS/safety query
        if any(word in query_lower for word in ['msds', 'safety', 'dangerous', 'hazardous', 'toxic']):
            return self.handle_safety_query(user, query)
        
        # Build context for AI
        context = self.build_context(user, query)
        
        # AI Provider configuration
        api_endpoint = "https://openrouter.ai/api/v1/chat completions"
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not api_key:
            return Response({
                "answer": "AI service is temporarily unavailable. Please try again later."
            }, status=status.HTTP_200_OK)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        prompt = self.build_prompt(user, query, context)
        
        payload = {
            "model": "openai/gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a helpful lab assistant for a high school science lab. Provide clear, safe, and practical guidance for experiments and lab procedures."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        try:
            ai_response = requests.post(api_endpoint, json=payload, headers=headers, timeout=15)
            ai_response.raise_for_status()
            
            data = ai_response.json()
            answer = data["choices"][0]["message"]["content"]
            
            return Response({"answer": answer}, status=status.HTTP_200_OK)
            
        except requests.exceptions.RequestException as e:
            return Response({
                "answer": "I'm having trouble connecting to the AI service. Please try again in a moment."
            }, status=status.HTTP_200_OK)
        except (KeyError, IndexError):
            return Response({
                "answer": "I received an unexpected response. Please rephrase your question."
            }, status=status.HTTP_200_OK)
    
    def build_context(self, user, query):
        """Build context based on user query type"""
        context = {}
        
        # Check for inventory-related queries
        if any(word in query.lower() for word in ['chemical', 'equipment', 'stock', 'available']):
            # Get chemicals expiring soon
            expiring_chemicals = Chemical.objects.filter(
                expiry_date__lte=timezone.now() + timedelta(days=30)
            ).order_by('expiry_date')[:5]
            
            # Get low stock chemicals
            low_stock_chemicals = Chemical.objects.filter(
                quantity__lte=5
            ).order_by('quantity')[:5]
            
            context['expiring_chemicals'] = [
                f"{c.name} (expires {c.expiry_date})" 
                for c in expiring_chemicals
            ]
            
            context['low_stock_chemicals'] = [
                f"{c.name} (only {c.quantity} left)" 
                for c in low_stock_chemicals
            ]
        
        # Check for equipment queries
        if any(word in query.lower() for word in ['equipment', 'tool', 'device']):
            broken_equipment = Equipment.objects.filter(
                condition='broken'
            ).order_by('name')
            
            context['broken_equipment'] = [
                e.name for e in broken_equipment
            ]
        
        return context
    
    def build_prompt(self, user, query, context):
        """Build the prompt for the AI based on user role and context"""
        
        prompt_parts = [
            f"User Role: {user.role}",
            f"Query: {query}",
            "Context:"
        ]
        
        if context.get('expiring_chemicals'):
            prompt_parts.append(f"Expiring chemicals: {', '.join(context['expiring_chemicals'])}")
        
        if context.get('low_stock_chemicals'):
            prompt_parts.append(f"Low stock chemicals: {', '.join(context['low_stock_chemicals'])}")
        
        if context.get('broken_equipment'):
            prompt_parts.append(f"Broken equipment: {', '.join(context['broken_equipment'])}")
        
        if user.role == 'student':
            prompt_parts.extend([
                "Provide basic safety guidance appropriate for high school students.",
                "Focus on general safety rules and when to ask for help.",
                "Do not provide detailed hazardous procedures."
            ])
        else:
            prompt_parts.extend([
                "Provide clear, practical guidance appropriate for a high school lab.",
                "Focus on safety and step-by-step instructions.",
                "If the query involves safety procedures, emphasize safety precautions."
            ])
        
        return "\n".join(prompt_parts)

    def handle_safety_query(self, user, query):
        """Handle safety-related queries with appropriate role-based responses"""
        
        # Extract chemical name from query
        chemical_name = None
        query_words = query.lower().split()
        
        # Simple extraction - look for chemical names in inventory
        chemicals = Chemical.objects.all()
        for chemical in chemicals:
            if chemical.name.lower() in query.lower():
                chemical_name = chemical.name
                break
        
        if chemical_name:
            try:
                chemical = Chemical.objects.get(name__iexact=chemical_name)
                
                if user.role == 'student':
                    # Provide basic safety info for students
                    safety_summary = f"""
                    **Basic Safety Information for {chemical.name} ({chemical.form}):**
                    
                    **Storage Location:** {chemical.storage_location}
                    **Danger Level:** {chemical.danger_classification}
                    
                    **Basic Safety Rules:**
                    • Always wear safety goggles and lab coat
                    • Never taste or smell directly
                    • Use in well-ventilated area
                    • Ask your teacher before handling
                    
                    **If you need detailed safety information:**
                    Please ask your teacher or lab assistant for the complete safety data sheet.
                    """
                    
                    return Response({"answer": safety_summary}, status=status.HTTP_200_OK)
                
                else:
                    # Teachers and assistants get full access
                    return self.get_full_safety_info(chemical, user)
                    
            except Chemical.DoesNotExist:
                return Response({
                    "answer": f"I couldn't find {chemical_name} in our inventory. Please check the spelling or ask about a different chemical."
                }, status=status.HTTP_200_OK)
        
        # General safety guidance
        if user.role == 'student':
            general_safety = """
            **General Lab Safety Guidelines:**
            
            • Always wear safety goggles and lab coat
            • Never eat, drink, or taste chemicals
            • Report any spills to your teacher immediately
            • Know the location of safety equipment (eyewash, fire extinguisher)
            • Always ask for help if you're unsure about procedures
            
            **For specific chemical safety:**
            Please ask your teacher for detailed safety information about specific chemicals.
            """
            return Response({"answer": general_safety}, status=status.HTTP_200_OK)
        
        else:
            # Teachers/assistants get AI-generated response
            return self.get_ai_safety_response(query, user)

    def get_full_safety_info(self, chemical, user):
        """Provide full safety information for teachers and assistants"""
        
        safety_info = f"""
        **Complete Safety Information for {chemical.name} ({chemical.form}):**
        
        **Storage:** {chemical.storage_location}
        **Danger Level:** {chemical.danger_classification}
        **Expiry Date:** {chemical.expiry_date}
        **Quantity Available:** {chemical.quantity}
        
        **MSDS File:** {'Available' if chemical.msds_file else 'Not available - consult teacher'}
        
        **Handling Precautions:**
        Based on danger level {chemical.danger_classification}:
        - Green: Safe for all users with basic precautions
        - Yellow: Requires teacher/assistant supervision
        - Red: Teacher only - requires special handling
        
        For complete MSDS information, please check the uploaded safety data sheet.
        """
        
        return Response({"answer": safety_info}, status=status.HTTP_200_OK)

    def get_ai_safety_response(self, query, user):
        """Get AI-generated safety response for teachers/assistants"""
        
        api_endpoint = "https://openrouter.ai/api/v1/chat/completions"
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not api_key:
            return Response({
                "answer": "AI service temporarily unavailable. Please consult lab safety materials."
            }, status=status.HTTP_200_OK)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        prompt = f"""
        User Role: {user.role}
        Query: {query}
        
        Provide detailed safety guidance for high school lab procedures.
        Include specific safety precautions and emergency procedures.
        """
        
        payload = {
            "model": "openai/gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a lab safety expert. Provide detailed safety guidance for high school science labs."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 400,
            "temperature": 0.6
        }
        
        try:
            ai_response = requests.post(api_endpoint, json=payload, headers=headers, timeout=15)
            ai_response.raise_for_status()
            
            data = ai_response.json()
            answer = data["choices"][0]["message"]["content"]
            
            return Response({"answer": answer}, status=status.HTTP_200_OK)
            
        except Exception:
            return Response({
                "answer": "Unable to generate detailed safety response. Please consult lab safety materials."
            }, status=status.HTTP_200_OK)


class MSDSQueryView(APIView):
    """Specialized endpoint for MSDS-related queries"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        chemical_name = request.data.get("chemical_name", "").strip()
        
        if not chemical_name:
            return Response({"detail": "Chemical name required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            chemical = Chemical.objects.filter(name__icontains=chemical_name).first()
            
            if not chemical:
                return Response({
                    "answer": f"I couldn't find {chemical_name} in our inventory. Please check the spelling or ask about a different chemical."
                })
            
            if not chemical.msds_file:
                return Response({
                    "answer": f"I found {chemical.name}, but the MSDS file is not available. Please ask your teacher for safety information."
                })
            
            # Build safety summary
            safety_info = {
                "name": chemical.name,
                "form": chemical.form,
                "danger_level": chemical.danger_classification,
                "storage_location": chemical.storage_location,
                "expiry_date": chemical.expiry_date.strftime("%Y-%m-%d"),
                "msds_available": bool(chemical.msds_file)
            }
            
            prompt = f"""
            Provide a brief safety summary for {chemical.name} ({chemical.form}) in a high school lab.
            Danger level: {chemical.danger_classification}
            Storage: {chemical.storage_location}
            Expiry: {chemical.expiry_date}
            
            Focus on:
            1. Basic safety precautions
            2. Proper handling procedures
            3. Storage requirements
            4. What to do in case of spills or exposure
            
            Keep it concise and appropriate for high school students.
            """
            
            return Response({"answer": prompt}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "answer": "Error retrieving chemical information. Please try again."
            }, status=status.HTTP_200_OK)
