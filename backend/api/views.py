# backend/api/views.py
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserMedia
from .serializers import UserSerializer, UserMediaSerializer
from .utils import process_media
import logging

logger = logging.getLogger(__name__)

class SignupView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        print("Signup request:", request.data)
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                },
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        print("Signup errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        print(f"Login attempt - Username: {username}")
        
        if not username or not password:
            return Response(
                {'error': 'Please provide both username and password'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        
        if user:
            print(f"Login successful for: {username}")
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                },
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        else:
            print(f"Login failed for: {username}")
            return Response(
                {'error': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

class MediaUploadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Determine media type
        content_type = file.content_type
        if 'image' in content_type:
            media_type = 'image'
        elif 'video' in content_type:
            media_type = 'video'
        else:
            return Response({'error': 'Unsupported file type'}, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"Processing upload: {file.name} ({media_type})")
        
        # Process for detection
        detection_results = process_media(file, media_type)
        
        # Save to database
        media = UserMedia.objects.create(
            user=request.user,
            file=file,
            media_type=media_type,
            file_name=file.name,
            file_size=file.size,
            objects_detected=detection_results.get('objects_detected', []),
            tags=detection_results.get('tags', []),
            faces_detected=detection_results.get('faces_detected', {'count': 0, 'locations': []}),
            labels=detection_results.get('labels', [])
        )
        
        serializer = UserMediaSerializer(media)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MediaListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        media = UserMedia.objects.filter(user=request.user)
        serializer = UserMediaSerializer(media, many=True)
        return Response(serializer.data)

class MediaSearchView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '').strip().lower()
        if not query:
            return Response({'error': 'No search query'}, status=400)
        
        print(f"Searching for: {query}")
        
        # Start with base queryset
        media = UserMedia.objects.filter(user=request.user)
        
        # Search in objects_detected and tags fields
        media = media.filter(
            Q(objects_detected__icontains=query) |
            Q(tags__icontains=query) |
            Q(labels__icontains=query)
        )
        
        # Category mappings for better search
        category_map = {
            'person': ['person', 'people', 'human', 'man', 'woman', 'child'],
            'people': ['person', 'people', 'human', 'man', 'woman', 'child'],
            'chair': ['chair', 'seat', 'stool'],
            'car': ['car', 'vehicle', 'automobile', 'truck'],
            'vehicle': ['car', 'vehicle', 'automobile', 'truck', 'bus', 'motorcycle'],
            'dog': ['dog', 'puppy', 'canine'],
            'cat': ['cat', 'kitten', 'feline'],
            'animal': ['dog', 'cat', 'bird', 'horse', 'cow', 'elephant'],
            'food': ['food', 'banana', 'apple', 'sandwich', 'pizza', 'cake', 'orange'],
            'phone': ['cell phone', 'mobile', 'phone', 'smartphone'],
            'computer': ['laptop', 'computer', 'pc', 'notebook'],
            'table': ['table', 'desk', 'dining table'],
            'face': ['face', 'faces', 'person'],
        }
        
        # If query matches a category, search for all related terms
        if query in category_map:
            category_terms = category_map[query]
            category_filter = Q()
            for term in category_terms:
                category_filter |= Q(objects_detected__icontains=term)
                category_filter |= Q(tags__icontains=term)
                category_filter |= Q(labels__icontains=term)
            
            # Get media that matches either original query or category
            category_media = UserMedia.objects.filter(user=request.user).filter(category_filter)
            
            # Combine both querysets
            media = (media | category_media).distinct()
        
        # Get distinct results
        media = media.distinct()
        
        print(f"Found {media.count()} results for '{query}'")
        
        serializer = UserMediaSerializer(media, many=True)
        return Response(serializer.data)

class DeleteMediaView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, media_id):
        try:
            media = UserMedia.objects.get(id=media_id, user=request.user)
            if media.file:
                media.file.delete()
            if media.thumbnail:
                media.thumbnail.delete()
            media.delete()
            return Response({'message': 'Media deleted successfully'})
        except UserMedia.DoesNotExist:
            return Response({'error': 'Media not found'}, status=status.HTTP_404_NOT_FOUND)