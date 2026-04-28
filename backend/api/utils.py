# backend/api/utils.py
import torch
import torchvision
from torchvision import transforms
from PIL import Image
import cv2
import numpy as np
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
import io
import os

class ObjectDetectionModel:
    def __init__(self):
        print("Loading object detection model...")
        try:
            # Load pre-trained Faster R-CNN model
            self.model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
            self.model.eval()
            
            # Move to CPU or GPU
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.model = self.model.to(self.device)
            print(f"Model loaded on {self.device}")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None
        
        # COCO classes from the model (91 classes)
        self.COCO_CLASSES = [
            '__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
            'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign',
            'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
            'elephant', 'bear', 'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A',
            'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl',
            'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
            'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'N/A', 'dining table',
            'N/A', 'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 
            'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'N/A',
            'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
        
        # Synonyms for better search
        self.synonyms = {
            'chair': ['chair', 'seat', 'stool', 'throne'],
            'person': ['person', 'people', 'human', 'man', 'woman', 'child', 'boy', 'girl'],
            'car': ['car', 'vehicle', 'automobile', 'truck', 'bus', 'van'],
            'dog': ['dog', 'puppy', 'canine'],
            'cat': ['cat', 'kitten', 'feline'],
            'table': ['table', 'desk', 'dining table', 'counter'],
            'computer': ['laptop', 'computer', 'pc', 'notebook'],
            'phone': ['cell phone', 'mobile', 'phone', 'smartphone'],
            'food': ['food', 'meal', 'dish', 'banana', 'apple', 'sandwich', 'pizza', 'cake'],
            'drink': ['bottle', 'cup', 'glass', 'wine glass', 'drink'],
            'animal': ['animal', 'bird', 'cat', 'dog', 'horse', 'cow', 'elephant'],
            'furniture': ['chair', 'couch', 'table', 'bed', 'desk', 'sofa'],
            'electronics': ['tv', 'laptop', 'computer', 'phone', 'keyboard', 'mouse'],
            'sports': ['ball', 'frisbee', 'skateboard', 'surfboard', 'tennis racket'],
            'outdoor': ['bicycle', 'motorcycle', 'boat', 'airplane', 'umbrella'],
            'indoor': ['book', 'clock', 'vase', 'microwave', 'oven', 'refrigerator']
        }

    def detect_objects(self, image_file, confidence_threshold=0.6):
        """Detect objects in an image with higher accuracy"""
        if self.model is None:
            print("Model not loaded!")
            return [], [], []
            
        try:
            # Open image
            if isinstance(image_file, (InMemoryUploadedFile, TemporaryUploadedFile)):
                image = Image.open(image_file).convert('RGB')
                image_file.seek(0)
            else:
                image = Image.open(image_file).convert('RGB')
            
            # Transform image
            transform = transforms.Compose([transforms.ToTensor()])
            image_tensor = transform(image).unsqueeze(0).to(self.device)
            
            # Run detection
            with torch.no_grad():
                predictions = self.model(image_tensor)
            
            # Extract detected objects with high confidence
            detected_objects = []
            scores = predictions[0]['scores'].cpu().numpy()
            labels = predictions[0]['labels'].cpu().numpy()
            boxes = predictions[0]['boxes'].cpu().numpy()
            
            print(f"Found {len(scores)} potential detections")
            
            for i, score in enumerate(scores):
                if score > confidence_threshold:
                    label_idx = labels[i]
                    if label_idx < len(self.COCO_CLASSES):
                        object_name = self.COCO_CLASSES[label_idx]
                        if object_name != 'N/A' and object_name != '__background__':
                            detected_objects.append({
                                'object': object_name,
                                'confidence': float(score),
                                'bbox': boxes[i].tolist()
                            })
                            print(f"Detected: {object_name} with confidence {score:.2f}")
            
            # Get unique object names
            unique_objects = list(set([obj['object'] for obj in detected_objects]))
            
            # Generate searchable tags (including synonyms)
            all_tags = set(unique_objects)
            
            # Add synonyms for detected objects
            for obj in unique_objects:
                for key, synonyms in self.synonyms.items():
                    if obj in synonyms or obj == key:
                        all_tags.add(key)
                        all_tags.update(synonyms)
            
            # Add categories
            for obj in unique_objects:
                for category, items in self.synonyms.items():
                    if obj in items:
                        all_tags.add(category)
            
            print(f"Detected unique objects: {unique_objects}")
            print(f"Generated search tags: {all_tags}")
            
            return unique_objects, list(all_tags), detected_objects
            
        except Exception as e:
            print(f"Object detection error: {e}")
            import traceback
            traceback.print_exc()
            return [], [], []
    
    def detect_faces(self, image_file):
        """Detect faces in image"""
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            if isinstance(image_file, (InMemoryUploadedFile, TemporaryUploadedFile)):
                file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
                image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                image_file.seek(0)
            else:
                image = cv2.imread(str(image_file))
            
            if image is None:
                return 0, []
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            return len(faces), faces.tolist()
            
        except Exception as e:
            print(f"Face detection error: {e}")
            return 0, []

# Initialize model
detection_model = ObjectDetectionModel()

def process_media(file, file_type):
    """Process uploaded media for detection"""
    try:
        if file_type == 'image':
            print(f"\n--- Processing image: {file.name} ---")
            objects, tags, objects_detailed = detection_model.detect_objects(file)
            face_count, faces = detection_model.detect_faces(file)
            
            # Add face-related tags
            if face_count > 0:
                tags.append('face')
                tags.append('people')
                if face_count == 1:
                    tags.append('person')
            
            # Ensure we have at least some tags
            if not tags:
                tags = ['image', 'uploaded']
            
            print(f"Final objects: {objects}")
            print(f"Final tags: {tags}")
            print(f"Faces found: {face_count}")
            
            return {
                'objects_detected': objects,
                'tags': list(set(tags)),  # Remove duplicates
                'faces_detected': {'count': face_count, 'locations': faces},
                'labels': list(set(tags))  # For search compatibility
            }
        else:
            return {
                'objects_detected': [],
                'tags': ['video'],
                'faces_detected': {'count': 0, 'locations': []},
                'labels': ['video']
            }
    except Exception as e:
        print(f"Error processing media: {e}")
        import traceback
        traceback.print_exc()
        return {
            'objects_detected': [],
            'tags': ['upload'],
            'faces_detected': {'count': 0, 'locations': []},
            'labels': ['upload']
        }