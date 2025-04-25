import asyncio
import os
import io
from client.comfyui import ComfyUI
from PIL import Image

async def test_text_to_image():
    # ComfyUI 서버 연결 설정
    comfy = ComfyUI(
        url=f'http://{os.environ.get("COMFYUI_HOST", "localhost")}:{os.environ.get("COMFYUI_PORT", 8188)}'
    )

    # 테스트할 파라미터 설정
    params = {
        "text": "Flowers in a vase, highly detailed, 4k",  # 프롬프트 텍스트
        "seed": 42,  # 시드값
        "steps": 20,  # 스텝 수
        "cfg": 8.0,  # CFG Scale
        "denoise": 1.0,  # Denoising strength
    }

    try:
        # 워크플로우 실행
        print("워크플로우 실행 중...")
        images = await comfy.process_workflow("text_to_image", params, return_url=False)
        
        # 결과 이미지 처리
        print(f"생성된 이미지 수: {sum(len(node_images) for node_images in images.values())}")
        
        # test 폴더 생성
        os.makedirs("test", exist_ok=True)
        
        # 이미지 데이터 확인 및 표시
        for node_id, node_images in images.items():
            print(f"\nNode {node_id}에서 생성된 이미지:")
            for idx, image_data in enumerate(node_images):
                # 바이트 데이터를 PIL Image로 변환
                image = Image.open(io.BytesIO(image_data))
                print(f"이미지 {idx + 1} 크기: {image.size}")
                
                # test 폴더에 이미지 저장
                save_path = os.path.join("test", f"test_output_{node_id}_{idx}.png")
                image.save(save_path)
                print(f"이미지 저장됨: {save_path}")

    except Exception as e:
        print(f"에러 발생: {str(e)}")

if __name__ == "__main__":
    # 테스트 실행
    asyncio.run(test_text_to_image())
