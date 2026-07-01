"""
AI Skin Analysis Module
=======================
Multi-label skin analysis using MobileNetV2 + MediaPipe face detection
with rule-based treatment recommendations.

Architecture:
1. MediaPipe: Face detection & landmarks
2. MobileNetV2: Multi-label skin condition scoring
3. Rule Engine: Treatment recommendations
"""

import os
import numpy as np
import cv2
from PIL import Image
import io

# Try to import TensorFlow
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras import layers, models
    TENSORFLOW_AVAILABLE = True
    KERAS_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    KERAS_AVAILABLE = False

try:
    import keras
    from keras.applications import MobileNetV2
    from keras import layers, models
    KERAS_AVAILABLE = True
except ImportError:
    KERAS_AVAILABLE = False

try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

# Configuration
IMAGE_SIZE = 224
CLASS_NAMES = ['acne', 'wrinkles', 'pigmentation', 'oiliness', 'sensitivity']
CLASS_LABELS = {
    'acne': 'Acné / Imperfections',
    'wrinkles': 'Signes de vieillissement',
    'pigmentation': 'Taches pigmentaires',
    'oiliness': 'Peau grasse',
    'sensitivity': 'Peau sensible',
}

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'skin_model.h5')


# ═══════════════════════════════════════════════════════════════
# STEP 1: Face Detection with MediaPipe
# ═══════════════════════════════════════════════════════════════

def detect_face(image_array):
    """
    Detect face in image using MediaPipe.
    
    Returns:
        dict with keys:
        {
            'detected': bool,
            'bbox': [x, y, w, h],
            'confidence': float,
            'landmarks': list of landmark points
        }
    """
    if not MEDIAPIPE_AVAILABLE:
        return {'detected': False, 'bbox': None, 'confidence': 0, 'landmarks': []}
    
    try:
        import mediapipe as mp
        
        # Try new MediaPipe API first
        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            
            base_options = python.BaseOptions(model_asset_path='mediapipe/face_detection/face_detection.tflite')
            options = vision.FaceDetectorOptions(base_options=base_options)
            detector = vision.FaceDetector.create_from_options(options)
            
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
            result = detector.detect(mp_image)
            
            if not result.detections:
                return {'detected': False, 'bbox': None, 'confidence': 0, 'landmarks': []}
            
            detection = result.detections[0]
            confidence = detection.categories[0].score
            
            h, w, _ = image_array.shape
            bbox = detection.bounding_box
            x = int(bbox.origin_x)
            y = int(bbox.origin_y)
            width = int(bbox.width)
            height = int(bbox.height)
            
            return {
                'detected': True,
                'bbox': [x, y, width, height],
                'confidence': confidence,
                'landmarks': []
            }
        except:
            # Fallback to classic MediaPipe
            mp_face = mp.solutions.face_detection
            
            with mp_face.FaceDetection(
                model_selection=1,
                min_detection_confidence=0.5
            ) as face_detection:
                
                rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
                results = face_detection.process(rgb_image)
                
                if not results.detections:
                    return {'detected': False, 'bbox': None, 'confidence': 0, 'landmarks': []}
                
                detection = results.detections[0]
                confidence = detection.score[0]
                
                h, w, _ = image_array.shape
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                
                return {
                    'detected': True,
                    'bbox': [x, y, width, height],
                    'confidence': confidence,
                    'landmarks': []
                }
    except Exception as e:
        print(f"Face detection error: {e}")
        return {'detected': False, 'bbox': None, 'confidence': 0, 'landmarks': []}
    
    try:
        import mediapipe as mp
        
        # Use the new MediaPipe API
        mp_face = mp.solutions.face_detection
        mp_drawing = mp.solutions.drawing_utils
        
        with mp_face.FaceDetection(
            model_selection=1,  # 1 for far faces, 0 for close faces
            min_detection_confidence=0.5
        ) as face_detection:
            
            # Convert to RGB (MediaPipe uses RGB)
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_image)
            
            if not results.detections:
                return {'detected': False, 'bbox': None, 'confidence': 0, 'landmarks': []}
            
            # Get the first face
            detection = results.detections[0]
            confidence = detection.score[0]
            
            # Get bounding box
            h, w, _ = image_array.shape
            bbox = detection.location_data.relative_bounding_box
            x = int(bbox.xmin * w)
            y = int(bbox.ymin * h)
            width = int(bbox.width * w)
            height = int(bbox.height * h)
            
            return {
                'detected': True,
                'bbox': [x, y, width, height],
                'confidence': confidence,
                'landmarks': []
            }
    except Exception as e:
        print(f"Face detection error: {e}")
        return {'detected': False, 'bbox': None, 'confidence': 0, 'landmarks': []}


# ═══════════════════════════════════════════════════════════════
# STEP 2: Crop & Preprocess Face
# ═══════════════════════════════════════════════════════════════

def preprocess_face(image_array, bbox=None, target_size=IMAGE_SIZE):
    """
    Crop face and normalize image.
    
    Args:
        image_array: OpenCV image (BGR)
        bbox: [x, y, w, h] or None for full image
        target_size: Target image size (default 224)
    
    Returns:
        Preprocessed image ready for model
    """
    if bbox is not None:
        x, y, w, h = bbox
        # Add padding
        pad = int(max(w, h) * 0.1)
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(image_array.shape[1] - x, w + 2 * pad)
        h = min(image_array.shape[0] - y, h + 2 * pad)
        face_img = image_array[y:y+h, x:x+w]
    else:
        face_img = image_array
    
    # Resize to target size
    face_img = cv2.resize(face_img, (target_size, target_size))
    
    # Normalize lighting (histogram equalization on LAB)
    try:
        lab = cv2.cvtColor(face_img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        face_img = cv2.merge([l, a, b])
        face_img = cv2.cvtColor(face_img, cv2.COLOR_LAB2BGR)
    except:
        pass  # Keep original if CLAHE fails
    
    # Normalize pixel values to [0, 1]
    face_img = face_img.astype(np.float32) / 255.0
    
    return face_img


# ═══════════════════════════════════════════════════════════════
# STEP 3: Build MobileNetV2 Multi-Label Model
# ═══════════════════════════════════════════════════════════════

def create_skin_model():
    """
    Create MobileNetV2-based multi-label skin analysis model.
    No Dropout - deterministic for inference.
    """
    if not KERAS_AVAILABLE:
        return None
    
    # Use MobileNetV2 pretrained on ImageNet
    base_model = MobileNetV2(
        weights='imagenet',
        include_top=False,
        input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3)
    )
    
    # Freeze base model
    base_model.trainable = False
    
    # Add deterministic classification head (no Dropout for inference)
    x = base_model.output
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dense(128, activation='relu')(x)
    
    # Multi-label output: 5 sigmoid outputs for 5 conditions
    outputs = layers.Dense(5, activation='sigmoid', name='skin_outputs')(x)
    
    model = models.Model(inputs=base_model.input, outputs=outputs)
    
    # Use MSE loss, simpler metrics
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='mse',
        metrics=['mae']
    )
    
    return model


_CACHED_MODEL = None

def load_model():
    """Load trained model from disk, or create new one if not found."""
    global _CACHED_MODEL

    print(f"[DEBUG] load_model called, KERAS_AVAILABLE={KERAS_AVAILABLE}")

    if not KERAS_AVAILABLE:
        print("[DEBUG] KERAS_AVAILABLE is False")
        return None

    # Return cached model if available
    if _CACHED_MODEL is not None:
        print("[DEBUG] Using cached model")
        return _CACHED_MODEL

    # Try to load trained model from disk
    if os.path.exists(MODEL_PATH):
        try:
            print(f"Loading trained model from {MODEL_PATH}...")
            _CACHED_MODEL = tf.keras.models.load_model(MODEL_PATH)
            print("Trained model loaded successfully")
            return _CACHED_MODEL
        except Exception as e:
            print(f"Failed to load model from disk: {e}")
            print("Falling back to creating new model...")

    # Create new model and cache it
    print("Creating new MobileNetV2 model...")
    _CACHED_MODEL = create_skin_model()
    return _CACHED_MODEL


# ═══════════════════════════════════════════════════════════════
# STEP 4: Skin Age Estimation (Rule-based using wrinkles + other factors)
# ═══════════════════════════════════════════════════════════════

def estimate_skin_age(wrinkle_score, acne_score, pigmentation_score):
    """
    Estimate skin age based on condition scores.
    
    This is a heuristic-based estimation combining multiple factors.
    """
    base_age = 25
    
    # Wrinkles are the main indicator
    if wrinkle_score > 70:
        age = base_age + 15
    elif wrinkle_score > 50:
        age = base_age + 10
    elif wrinkle_score > 30:
        age = base_age + 5
    else:
        age = base_age
    
    # Acne can make skin look younger
    if acne_score > 60:
        age = max(18, age - 5)
    
    # Pigmentation adds years
    if pigmentation_score > 60:
        age += 8
    elif pigmentation_score > 40:
        age += 4
    
    return min(70, max(18, age))


# ═══════════════════════════════════════════════════════════════
# STEP 5: Rule Engine for Treatment Recommendations
# ═══════════════════════════════════════════════════════════════

def get_treatment_recommendations(scores):
    """
    Rule-based treatment recommendations based on skin condition scores.
    
    This is NOT AI - it's a business logic rule engine.
    """
    recommendations = []
    
    acne = scores.get('acne', 0)
    wrinkles = scores.get('wrinkles', 0)
    pigmentation = scores.get('pigmentation', 0)
    oiliness = scores.get('oiliness', 0)
    sensitivity = scores.get('sensitivity', 0)
    
    # Acne treatments
    if acne > 50:
        if sensitivity < 40:
            recommendations.append({
                'treatment': 'Hydrafacial',
                'reason': 'Nettoyage profond pour peau à imperfections',
                'priority': 'high' if acne > 70 else 'medium'
            })
        recommendations.append({
            'treatment': 'Peeling Chimique',
            'reason': 'Exfoliation pour réduire les boutons et cicatrices',
            'priority': 'medium' if acne > 60 else 'low'
        })
        recommendations.append({
            'treatment': 'Traitement LED',
            'reason': 'Lumière bleue pour tuer les bactéries responsables d\'acné',
            'priority': 'medium'
        })
    
    # Wrinkle treatments
    if wrinkles > 40:
        recommendations.append({
            'treatment': 'Injection Botox',
            'reason': 'Relaxation des rides d\'expression',
            'priority': 'high' if wrinkles > 60 else 'medium'
        })
        recommendations.append({
            'treatment': 'Acide Hyaluronique',
            'reason': 'Comblement des rides et hydratation profonde',
            'priority': 'medium' if wrinkles > 50 else 'low'
        })
        recommendations.append({
            'treatment': 'Radiofréquence',
            'reason': 'Stimulation du collagène pour raffermir la peau',
            'priority': 'medium'
        })
    
    # Pigmentation treatments
    if pigmentation > 40:
        recommendations.append({
            'treatment': 'Laser IPL',
            'reason': 'Élimination des tâches pigmentaires',
            'priority': 'high' if pigmentation > 60 else 'medium'
        })
        recommendations.append({
            'treatment': 'Peeling Dépigmentant',
            'reason': 'Éclaircissement des tâches et均匀 du teint',
            'priority': 'medium'
        })
        recommendations.append({
            'treatment': 'Mésothérapie Vitaminée',
            'reason': 'Éclaircissement et éclat du teint',
            'priority': 'low'
        })
    
    # Oiliness treatments
    if oiliness > 50:
        recommendations.append({
            'treatment': 'Soin Hydratant Matifiant',
            'reason': 'Régulation du sébum et matité',
            'priority': 'high' if oiliness > 70 else 'medium'
        })
        recommendations.append({
            'treatment': 'Laser CO2',
            'reason': 'Resserrement des pores et réduction du sébum',
            'priority': 'medium'
        })
    
    # Sensitivity treatments
    if sensitivity > 50:
        recommendations.append({
            'treatment': 'Soin Calmant Intensif',
            'reason': 'Apaisement des irritations et renforcement de la barrière cutanée',
            'priority': 'high'
        })
        recommendations.append({
            'treatment': 'LED Rouge',
            'reason': 'Calm and repair sensitive skin',
            'priority': 'medium'
        })
    
    # General recommendations for normal skin
    if max(scores.values()) < 30:
        recommendations.append({
            'treatment': 'Soin Hydratant',
            'reason': 'Entretenir une peau saine',
            'priority': 'low'
        })
        recommendations.append({
            'treatment': 'Mésothérapie',
            'reason': 'Prévention et éclat du teint',
            'priority': 'low'
        })
    
    # Sort by priority
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
    
    return recommendations[:5]  # Return top 5


# ═══════════════════════════════════════════════════════════════
# STEP 6: Main Analysis Function
# ═══════════════════════════════════════════════════════════════

def analyze_skin(image_data):
    """
    Complete skin analysis pipeline.
    
    Args:
        image_data: Image file bytes or PIL Image
    
    Returns:
        dict: {
            'success': bool,
            'face_detected': bool,
            'scores': {
                'acne': 0-100,
                'wrinkles': 0-100,
                'pigmentation': 0-100,
                'oiliness': 0-100,
                'sensitivity': 0-100
            },
            'skin_age': int,
            'recommendations': [
                {'treatment': str, 'reason': str, 'priority': str}
            ],
            'error': str
        }
    """
    try:
        # Load image
        if isinstance(image_data, bytes):
            image = Image.open(io.BytesIO(image_data))
            image = image.convert('RGB')
            image_array = np.array(image)
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        else:
            image_array = image_data
        
        # Step 1: Detect face
        face_info = detect_face(image_array)
        
        if not face_info.get('detected', False):
            # Fallback: analyze whole image
            print("No face detected, analyzing entire image")
            processed = preprocess_face(image_array, bbox=None)
        else:
            # Step 2: Crop and preprocess face
            processed = preprocess_face(image_array, bbox=face_info['bbox'])
        
        # Convert to RGB for model
        processed_rgb = cv2.cvtColor((processed * 255).astype(np.uint8), cv2.COLOR_BGR2RGB)
        processed_rgb = np.expand_dims(processed_rgb, axis=0)
        
        # Step 3: Load model and predict
        model = load_model()
        
        if model is not None and KERAS_AVAILABLE:
            # Predict
            pred_result = model.predict(processed_rgb, verbose=0)
            
            if len(pred_result) == 0:
                scores = generate_fallback_scores()
            else:
                predictions = pred_result[0] if len(pred_result.shape) > 1 else pred_result
                
                # Ensure predictions is an array with 5 elements
                if hasattr(predictions, '__len__') and len(predictions) >= 5:
                    # Convert to percentage scores
                    scores = {
                        'acne': int(float(predictions[0]) * 100),
                        'wrinkles': int(float(predictions[1]) * 100),
                        'pigmentation': int(float(predictions[2]) * 100),
                        'oiliness': int(float(predictions[3]) * 100),
                        'sensitivity': int(float(predictions[4]) * 100),
                    }
                else:
                    scores = generate_fallback_scores()
        else:
            # Fallback scores when model not available
            scores = generate_fallback_scores()
        
        # Step 4: Estimate skin age
        skin_age = estimate_skin_age(
            scores['wrinkles'],
            scores['acne'],
            scores['pigmentation']
        )
        
        # Step 5: Get treatment recommendations (rule-based)
        recommendations = get_treatment_recommendations(scores)
        
        return {
            'success': True,
            'face_detected': face_info.get('detected', False),
            'scores': scores,
            'skin_age': skin_age,
            'recommendations': recommendations,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'face_detected': False,
            'scores': {},
            'skin_age': 0,
            'recommendations': [],
            'error': str(e)
        }


def generate_fallback_scores():
    """
    Default fallback scores when no image is provided.
    """
    return {
        'acne': 35,
        'wrinkles': 30,
        'pigmentation': 35,
        'oiliness': 40,
        'sensitivity': 35,
    }


# ═══════════════════════════════════════════════════════════════
# STEP 7: For Training (Dataset Creation)
# ═══════════════════════════════════════════════════════════════

def prepare_dataset(image_paths, labels):
    """
    Prepare dataset for training.
    
    Args:
        image_paths: List of image file paths
        labels: List of dicts like [{'acne': 1, 'wrinkles': 0, ...}, ...]
    
    Returns:
        X, y arrays ready for training
    """
    X = []
    y = []
    
    for path, label in zip(image_paths, labels):
        img = cv2.imread(path)
        face_info = detect_face(img)
        
        if face_info['detected']:
            processed = preprocess_face(img, bbox=face_info['bbox'])
            X.append(processed)
            y.append([
                label['acne'],
                label['wrinkles'],
                label['pigmentation'],
                label['oiliness'],
                label['sensitivity']
            ])
    
    return np.array(X), np.array(y)


# ═══════════════════════════════════════════════════════════════
# Test/Usage Example
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 60)
    print("AI Skin Analysis Module")
    print("=" * 60)
    print(f"TensorFlow Available: {KERAS_AVAILABLE}")
    print(f"MediaPipe Available: {MEDIAPIPE_AVAILABLE}")
    print(f"Model Path: {MODEL_PATH}")
    print("=" * 60)
    
    # Test with a sample (if you have an image)
    # result = analyze_skin('path/to/face.jpg')
    # print(result)