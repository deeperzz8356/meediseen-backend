import os
import sys
import uuid
import asyncio
import httpx
from pathlib import Path

# Add root to sys.path to import model
sys.path.append(str(Path(__file__).resolve().parents[1]))

from model.graph import build_graph

async def test_local_pipeline():
    print("--- Starting Local Pipeline Test ---")
    
    # 1. Setup paths
    session_id = str(uuid.uuid4())
    base_dir = Path(__file__).resolve().parents[1]
    test_image_dir = base_dir / "uploads"
    test_image_dir.mkdir(exist_ok=True)
    
    # We need a dummy image for testing
    # If no image exists, we'll skip the actual CV2 part or use a placeholder
    test_image_path = test_image_dir / "test_input.jpg"
    if not test_image_path.exists():
        print(f"Please place a test image at {test_image_path} to run a full test.")
        # Create a tiny dummy image if possible
        try:
            from PIL import Image
            img = Image.new('RGB', (100, 100), color = (73, 109, 137))
            img.save(test_image_path)
            print("Created a dummy test image.")
        except ImportError:
            print("Could not create dummy image. Please provide one manually.")
            return

    # 2. Build Graph
    print("Building Graph...")
    graph = build_graph()
    
    # 3. Prepare State
    state = {
        "session_id": session_id,
        "image_path": str(test_image_path),
        "image_url": "http://placeholder.url/image.jpg",
        "user_symptoms": "Itching and redness on the arm for 3 days.",
        "prediction": "",
        "confidence_score": 0.0,
        "explanation": "",
        "db_context": "",
        "final_report": "",
        "heatmap_path": "",
        "report_path": "",
        "report_url": ""
    }
    
    # 4. Invoke Graph
    print("Invoking Graph (this calls the AI)...")
    try:
        result = graph.invoke(state)
        print("\n--- TEST SUCCESS ---")
        print(f"Diagnosis: {result['prediction']}")
        print(f"Confidence: {result['confidence_score']}")
        print(f"Final Report: {result['final_report'][:100]}...")
        print(f"Heatmap Path: {result['heatmap_path']}")
        print(f"Report Path: {result['report_path']}")
    except Exception as e:
        print(f"\n--- TEST FAILED ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_local_pipeline())
