"""
Gradio UI 구현
CT 영상 유효성 검증 리드 스터디 플랫폼의 사용자 인터페이스
"""
import gradio as gr
import asyncio
from typing import Optional, List, Tuple
import numpy as np
import inspect

from auth import validate_inspector_info, session
from database import db
from ct_utils import ct_processor, get_patient_list, WINDOW_PRESETS


# 전역 상태 관리
class AppState:
    """애플리케이션 상태 관리"""
    def __init__(self):
        self.current_patient_id = None
        self.current_slice_idx = 0
        self.window_level = 40.0
        self.window_width = 400.0
        self.num_slices = 0
        

app_state = AppState()


# 유틸리티 함수
def create_safe_html(value: str = "", **kwargs):
    """
    Gradio 버전 호환을 위한 HTML 컴포넌트 생성 래퍼
    sanitize_html 파라미터가 지원되지 않는 버전에서 자동으로 제거
    """
    try:
        sig = inspect.signature(gr.HTML.__init__)
        if "sanitize_html" not in sig.parameters:
            kwargs.pop("sanitize_html", None)
    except Exception:
        # 시그니처 조회 실패 시 보수적으로 제거
        kwargs.pop("sanitize_html", None)
    return gr.HTML(value=value, **kwargs)


def create_canvas_html(base64_data: str = None, width: int = 512, height: int = 512) -> str:
    """
    클라이언트 사이드 렌더링을 위한 Canvas HTML 생성
    
    Args:
        base64_data: Base64로 인코딩된 이미지 데이터
        width: 이미지 너비
        height: 이미지 높이
        
    Returns:
        Canvas HTML 문자열
    """
    # Base64를 안전하게 전달하기 위해 별도 script 태그에 담는다.
    # '</script>' 시퀀스로 스크립트가 조기 종료되지 않도록 '<\/'로 치환.
    data_text = base64_data.replace('</', '<\/') if base64_data else ''
    
    return f'''
    <div id="ct-canvas-container" style="display: flex; justify-content: center; background-color: #000; width: 100%; height: 100%;">
        <canvas id="ct-canvas" 
                width="{width}"
                height="{height}"
                data-original-width="{width}" 
                data-original-height="{height}"
                style="max-width: 100%; max-height: 100%; object-fit: contain; image-rendering: pixelated;">
        </canvas>
        <!-- 대용량 Base64는 속성에 넣지 않고 별도 스크립트 태그에 안전하게 보관 -->
        <script id="ct-data" type="application/octet-stream">{data_text}</script>
    </div>
    <script>
        (function() {{
            const container = document.getElementById('ct-canvas-container');
            const canvas = document.getElementById('ct-canvas');
            if (!canvas || !container) {{
                console.error('Canvas or container not found');
                return;
            }}
            
            const originalWidth = parseInt(canvas.getAttribute('data-original-width')) || {width};
            const originalHeight = parseInt(canvas.getAttribute('data-original-height')) || {height};
            const dataEl = document.getElementById('ct-data');
            const imageData = dataEl ? (dataEl.textContent || '').trim() : '';
            
            if (!imageData) {{
                console.log('No image data');
                canvas.width = originalWidth;
                canvas.height = originalHeight;
                const ctx = canvas.getContext('2d');
                ctx.fillStyle = '#000000';
                ctx.fillRect(0, 0, originalWidth, originalHeight);
                return;
            }}
            
            // Canvas의 실제 해상도는 원본 크기로 설정 (고해상도 유지)
            canvas.width = originalWidth;
            canvas.height = originalHeight;
            
            const ctx = canvas.getContext('2d');
            
            try {{
                // Base64 디코딩
                const binaryString = atob(imageData);
                const len = binaryString.length;
                const bytes = new Uint8Array(len);
                for (let i = 0; i < len; i++) {{
                    bytes[i] = binaryString.charCodeAt(i);
                }}
                
                const expectedLen = originalWidth * originalHeight * 3;  // RGB 형식
                console.log('Decoded', len, 'bytes for', originalWidth, 'x', originalHeight, 'image');
                
                if (len !== expectedLen) {{
                    console.error('Data length mismatch! Got', len, 'expected', expectedLen);
                }}
                
                // ImageData 생성 (RGBA 형식)
                const imgData = ctx.createImageData(originalWidth, originalHeight);
                
                // RGB 데이터를 RGBA로 변환
                let rgbIdx = 0;
                for (let i = 0; i < originalWidth * originalHeight; i++) {{
                    const rgbaIdx = i * 4;
                    imgData.data[rgbaIdx] = bytes[rgbIdx];         // R
                    imgData.data[rgbaIdx + 1] = bytes[rgbIdx + 1]; // G
                    imgData.data[rgbaIdx + 2] = bytes[rgbIdx + 2]; // B
                    imgData.data[rgbaIdx + 3] = 255;               // A
                    rgbIdx += 3;
                }}
                
                // Canvas에 그리기
                ctx.putImageData(imgData, 0, 0);
                console.log('Image rendered successfully');
            }} catch (e) {{
                console.error('Canvas rendering error:', e);
                console.error('Error stack:', e.stack);
            }}
        }})();
    </script>
    '''


# 이벤트 핸들러 함수들

async def handle_login(affiliation: str, name: str, password: str):
    """로그인 처리"""
    # 입력 검증
    is_valid, error_msg = validate_inspector_info(affiliation, name, password)
    
    if not is_valid:
        return (
            gr.update(visible=True),  # 로그인 페이지 유지
            gr.update(visible=False),  # 뷰어 페이지 숨김
            error_msg,  # 에러 메시지
            gr.update(),  # 환자 목록
            gr.update()   # 검사자 정보
        )
    
    # 검사자 정보 생성 또는 조회
    inspector_id = await db.get_or_create_inspector(affiliation, name)
    session.login(inspector_id, affiliation, name)
    
    # 환자 목록 로드
    patient_list = get_patient_list()
    results = await db.get_inspector_results(inspector_id)
    submitted_set = set(r["patient_id"] for r in results)
    
    # 환자 목록에 상태 표시
    patient_choices = []
    for patient_id in patient_list:
        status_icon = "[분석됨]" if patient_id in submitted_set else "[분석전]"
        patient_choices.append(f"{status_icon} {patient_id}")
    
    inspector_info = f"**검사자:** {affiliation} - {name}"
    
    return (
        gr.update(visible=False),  # 로그인 페이지 숨김
        gr.update(visible=True),   # 뷰어 페이지 표시
        "",  # 에러 메시지 초기화
        gr.update(choices=patient_choices, value=None),  # 환자 목록
        inspector_info  # 검사자 정보
    )


def handle_logout():
    """로그아웃 처리"""
    session.logout()
    ct_processor.clear()
    app_state.current_patient_id = None
    
    return (
        gr.update(visible=True),   # 로그인 페이지 표시
        gr.update(visible=False),  # 뷰어 페이지 숨김
        "",  # 입력 필드 초기화
        "",
        "",
        ""  # 에러 메시지 초기화
    )


async def handle_patient_select(patient_display: str):
    """환자 선택 처리"""
    if not patient_display:
        return (
            create_canvas_html(),
            "좌측 사이드바에서 환자를 선택해주세요.",
            gr.update(value=0, maximum=0),
            0,
            gr.update(value=40.0),
            gr.update(value=400.0),
            gr.update(value=None),
            "",
            gr.update(interactive=False)  # 제출 버튼 비활성화
        )
    
    # 환자 ID 추출 (상태 아이콘 제거)
    patient_id = patient_display.split(" ", 1)[1]
    
    # 볼륨 로드
    success = ct_processor.load_volume(patient_id)
    if not success:
        return (
            create_canvas_html(),
            f"환자 데이터를 로드할 수 없습니다: {patient_id}",
            gr.update(),
            0,
            gr.update(),
            gr.update(),
            gr.update(value=None),
            "",
            gr.update(interactive=False)  # 제출 버튼 비활성화
        )
    
    # 상태 업데이트
    app_state.current_patient_id = patient_id
    app_state.current_slice_idx = ct_processor.shape[0] // 2  # 중간 슬라이스로 시작
    app_state.num_slices = ct_processor.shape[0]
    
    # 분석 결과 확인
    inspector_id = session.get_inspector_id()
    result_data = await db.get_analysis_result(inspector_id, patient_id)
    
    if result_data:
        result_value = result_data["result"]
        result_info = f"최종 제출: {result_data['updated_at']}"
        submit_btn_state = gr.update(interactive=True)  # 기존 결과가 있으면 버튼 활성화
    else:
        result_value = None
        result_info = ""
        submit_btn_state = gr.update(interactive=False)  # 결과 없으면 버튼 비활성화
    
    # 첫 슬라이스 이미지 데이터 생성
    base64_data = ct_processor.get_slice_as_base64(
        app_state.current_slice_idx,
        app_state.window_level,
        app_state.window_width
    )
    
    canvas_html = create_canvas_html(
        base64_data,
        ct_processor.shape[2],  # width
        ct_processor.shape[1]   # height
    )
    
    info_text = f"**환자 ID:** {patient_id}, **슬라이스 수:** {app_state.num_slices}"
    
    return (
        canvas_html,
        info_text,
        gr.update(value=app_state.current_slice_idx, maximum=app_state.num_slices - 1, minimum=0),
        app_state.current_slice_idx,
        gr.update(value=app_state.window_level),
        gr.update(value=app_state.window_width),
        gr.update(value=result_value),
        result_info,
        submit_btn_state  # 제출 버튼 상태
    )


def update_slice_from_slider(slice_idx: int):
    """슬라이더에서 슬라이스 업데이트"""
    if app_state.current_patient_id is None:
        return create_canvas_html(), slice_idx
    
    app_state.current_slice_idx = slice_idx
    
    base64_data = ct_processor.get_slice_as_base64(
        slice_idx,
        app_state.window_level,
        app_state.window_width
    )
    
    canvas_html = create_canvas_html(
        base64_data,
        ct_processor.shape[2],
        ct_processor.shape[1]
    )
    
    return canvas_html, slice_idx


def update_slice_from_number(slice_num: int):
    """숫자 입력에서 슬라이스 업데이트"""
    if app_state.current_patient_id is None:
        return create_canvas_html(), gr.update(), 0
    
    # 범위 체크
    slice_num = max(0, min(slice_num, app_state.num_slices - 1))
    app_state.current_slice_idx = slice_num
    
    base64_data = ct_processor.get_slice_as_base64(
        slice_num,
        app_state.window_level,
        app_state.window_width
    )
    
    canvas_html = create_canvas_html(
        base64_data,
        ct_processor.shape[2],
        ct_processor.shape[1]
    )
    
    return canvas_html, gr.update(value=slice_num), slice_num


def update_window_level(level: float):
    """윈도우 레벨 업데이트"""
    if app_state.current_patient_id is None:
        return create_canvas_html(), level
    
    app_state.window_level = level
    
    base64_data = ct_processor.get_slice_as_base64(
        app_state.current_slice_idx,
        level,
        app_state.window_width
    )
    
    canvas_html = create_canvas_html(
        base64_data,
        ct_processor.shape[2],
        ct_processor.shape[1]
    )
    
    return canvas_html, level


def update_window_width(width: float):
    """윈도우 너비 업데이트"""
    if app_state.current_patient_id is None:
        return create_canvas_html(), width
    
    app_state.window_width = width
    
    base64_data = ct_processor.get_slice_as_base64(
        app_state.current_slice_idx,
        app_state.window_level,
        width
    )
    
    canvas_html = create_canvas_html(
        base64_data,
        ct_processor.shape[2],
        ct_processor.shape[1]
    )
    
    return canvas_html, width


def apply_window_preset(preset_name: str):
    """윈도우 프리셋 적용"""
    if app_state.current_patient_id is None or preset_name not in WINDOW_PRESETS:
        return create_canvas_html(), gr.update(), gr.update()
    
    preset = WINDOW_PRESETS[preset_name]
    app_state.window_level = preset["level"]
    app_state.window_width = preset["width"]
    
    base64_data = ct_processor.get_slice_as_base64(
        app_state.current_slice_idx,
        app_state.window_level,
        app_state.window_width
    )
    
    canvas_html = create_canvas_html(
        base64_data,
        ct_processor.shape[2],
        ct_processor.shape[1]
    )
    
    return (
        canvas_html,
        gr.update(value=app_state.window_level),
        gr.update(value=app_state.window_width)
    )


def handle_result_radio_change(result: str):
    """분석 결과 라디오 버튼 변경 처리"""
    # 선택된 값이 있으면 버튼 활성화, 없으면 비활성화
    return gr.update(interactive=result is not None)


async def submit_analysis_result(result: str):
    """분석 결과 제출"""
    if not session.is_authenticated():
        return "로그인이 필요합니다.", gr.update(), ""
    
    if app_state.current_patient_id is None:
        return "환자를 먼저 선택해주세요.", gr.update(), ""
    
    if result is None:
        return "결과를 선택해주세요.", gr.update(), ""
    
    # 결과 저장
    inspector_id = session.get_inspector_id()
    success = await db.save_analysis_result(
        inspector_id,
        app_state.current_patient_id,
        result
    )
    
    if success:
        # 환자 목록 업데이트
        patient_list = get_patient_list()
        results = await db.get_inspector_results(inspector_id)
        submitted_set = set(r["patient_id"] for r in results)
        
        patient_choices = []
        current_selection = None
        for patient_id in patient_list:
            status_icon = "[분석됨]" if patient_id in submitted_set else "[분석전]"
            display = f"{status_icon} {patient_id}"
            patient_choices.append(display)
            if patient_id == app_state.current_patient_id:
                current_selection = display
        
        from datetime import datetime
        result_info = f"최종 제출: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return (
            f"분석 결과가 성공적으로 제출되었습니다. (환자: {app_state.current_patient_id}, 결과: {result})",
            gr.update(choices=patient_choices, value=current_selection),
            result_info
        )
    else:
        return "분석 결과 저장 중 오류가 발생했습니다.", gr.update(), ""


# Gradio 인터페이스 구성
def create_ui():
    """Gradio UI 생성"""
    
    # 심플한 테마 설정
    simple_theme = gr.themes.Base(
        primary_hue="orange",
        secondary_hue="gray",
        neutral_hue="stone",
        font=gr.themes.GoogleFont("Inter"),
        font_mono=gr.themes.GoogleFont("IBM Plex Mono"),
    ).set(
        body_background_fill="*neutral_50",
        body_text_color="*neutral_900",
        button_primary_background_fill="*primary_600",
        button_primary_background_fill_hover="*primary_700",
        button_primary_text_color="white",
        button_secondary_background_fill="*neutral_100",
        button_secondary_background_fill_hover="*neutral_200",
        button_secondary_text_color="*neutral_900",
        border_color_primary="*neutral_200",
        block_background_fill="white",
        input_background_fill="white",
        slider_color="*primary_600",
    )
    
    with gr.Blocks(
        title="CT Read Study Platform",
        theme=simple_theme,
        js="""
        function() {
            // 라이트 모드 강제 적용
            document.body.classList.remove('dark');
            
            // 다크 모드 토글 버튼 숨기기
            const darkModeToggle = document.querySelector('.dark\\\\:bg-gray-950');
            if (darkModeToggle) {
                darkModeToggle.style.display = 'none';
            }
            
            // 시스템 다크모드 설정 무시
            if (window.matchMedia) {
                window.matchMedia('(prefers-color-scheme: dark)').matches = false;
            }
            
            // CT 이미지 제스처 컨트롤 설정
            setTimeout(() => {
                const imageContainer = document.querySelector('.image-display-container');
                if (!imageContainer) return;
                
                // 렌더링 함수: HTML 컴포넌트에 삽입된 script#ct-data로부터 Base64를 읽어 캔버스에 그리기
                const renderFromHtmlComponent = () => {
                    try {
                        const canvas = imageContainer.querySelector('#ct-canvas');
                        const dataEl = imageContainer.querySelector('#ct-data');
                        if (!canvas || !dataEl) return;
                        const width = parseInt(canvas.getAttribute('data-original-width')) || canvas.width || 512;
                        const height = parseInt(canvas.getAttribute('data-original-height')) || canvas.height || 512;
                        const imageData = (dataEl.textContent || '').trim();
                        if (!imageData) return;

                        const ctx = canvas.getContext('2d');
                        const binaryString = atob(imageData);
                        const len = binaryString.length;
                        const bytes = new Uint8Array(len);
                        for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i);
                        const expectedLen = width * height * 3; // RGB
                        if (len !== expectedLen) {
                            console.warn('[CT] RGB length mismatch', { len, expectedLen, width, height });
                        }
                        const imgData = ctx.createImageData(width, height);
                        let rgbIdx = 0;
                        for (let i = 0; i < width * height && rgbIdx + 2 < bytes.length; i++) {
                            const rgbaIdx = i * 4;
                            imgData.data[rgbaIdx] = bytes[rgbIdx];
                            imgData.data[rgbaIdx + 1] = bytes[rgbIdx + 1];
                            imgData.data[rgbaIdx + 2] = bytes[rgbIdx + 2];
                            imgData.data[rgbaIdx + 3] = 255;
                            rgbIdx += 3;
                        }
                        ctx.putImageData(imgData, 0, 0);
                    } catch (e) {
                        console.error('[CT] Render error', e);
                    }
                };

                // 최초 시도
                renderFromHtmlComponent();

                // 이미지 영역 변경 감지하여 렌더
                const observer = new MutationObserver(() => {
                    renderFromHtmlComponent();
                });
                observer.observe(imageContainer, { childList: true, subtree: true, characterData: true });

                let isRightMouseDown = false;
                let startX = 0;
                let startY = 0;
                let startLevel = 40;
                let startWidth = 400;
                
                // WL/WW 표시용 툴팁 생성
                const tooltip = document.createElement('div');
                tooltip.id = 'wl-ww-tooltip';
                tooltip.style.cssText = `
                    position: fixed;
                    background-color: rgba(0, 0, 0, 0.8);
                    color: white;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 14px;
                    font-family: monospace;
                    pointer-events: none;
                    z-index: 10000;
                    display: none;
                    white-space: nowrap;
                `;
                document.body.appendChild(tooltip);
                
                // 우클릭 메뉴 방지
                imageContainer.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                });
                
                // 마우스 다운
                imageContainer.addEventListener('mousedown', (e) => {
                    if (e.button === 2) { // 우클릭
                        isRightMouseDown = true;
                        startX = e.clientX;
                        startY = e.clientY;
                        
                        // 현재 윈도우 레벨/너비 값 가져오기
                        const levelSlider = document.querySelector('input[type="range"][aria-label*="윈도우 레벨"]');
                        const widthSlider = document.querySelector('input[type="range"][aria-label*="윈도우 너비"]');
                        if (levelSlider) startLevel = parseFloat(levelSlider.value);
                        if (widthSlider) startWidth = parseFloat(widthSlider.value);
                        
                        imageContainer.style.cursor = 'crosshair';
                        
                        // 툴팁 표시
                        tooltip.style.display = 'block';
                        tooltip.style.left = (e.clientX + 15) + 'px';
                        tooltip.style.top = (e.clientY + 15) + 'px';
                        tooltip.textContent = `WL: ${Math.round(startLevel)} / WW: ${Math.round(startWidth)}`;
                        
                        e.preventDefault();
                    }
                });
                
                // 마우스 무브
                imageContainer.addEventListener('mousemove', (e) => {
                    if (isRightMouseDown) {
                        const deltaX = e.clientX - startX;
                        const deltaY = e.clientY - startY;
                        
                        // 윈도우 레벨 조절 (좌/우 드래그)
                        const newLevel = Math.max(-1000, Math.min(1000, startLevel + deltaX));
                        const levelSlider = document.querySelector('input[type="range"][aria-label*="윈도우 레벨"]');
                        if (levelSlider && Math.abs(deltaX) > 2) {
                            levelSlider.value = newLevel;
                            levelSlider.dispatchEvent(new Event('input', { bubbles: true }));
                            levelSlider.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        
                        // 윈도우 너비 조절 (상/하 드래그) - 위로 드래그하면 증가
                        const newWidth = Math.max(1, Math.min(2000, startWidth - deltaY));
                        const widthSlider = document.querySelector('input[type="range"][aria-label*="윈도우 너비"]');
                        if (widthSlider && Math.abs(deltaY) > 2) {
                            widthSlider.value = newWidth;
                            widthSlider.dispatchEvent(new Event('input', { bubbles: true }));
                            widthSlider.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        
                        // 툴팁 위치 및 내용 업데이트
                        tooltip.style.left = (e.clientX + 15) + 'px';
                        tooltip.style.top = (e.clientY + 15) + 'px';
                        tooltip.textContent = `WL: ${Math.round(newLevel)} / WW: ${Math.round(newWidth)}`;
                        
                        e.preventDefault();
                    }
                });
                
                // 마우스 업
                const handleMouseUp = () => {
                    if (isRightMouseDown) {
                        isRightMouseDown = false;
                        imageContainer.style.cursor = 'default';
                        
                        // 툴팁 숨김
                        tooltip.style.display = 'none';
                        
                        // release 이벤트 트리거
                        const levelSlider = document.querySelector('input[type="range"][aria-label*="윈도우 레벨"]');
                        const widthSlider = document.querySelector('input[type="range"][aria-label*="윈도우 너비"]');
                        if (levelSlider) {
                            levelSlider.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        if (widthSlider) {
                            widthSlider.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }
                };
                
                imageContainer.addEventListener('mouseup', handleMouseUp);
                document.addEventListener('mouseup', handleMouseUp);
                
                // 휠 이벤트 (슬라이스 변경)
                imageContainer.addEventListener('wheel', (e) => {
                    e.preventDefault();
                    
                    const sliceSlider = document.querySelector('input[type="range"][aria-label*="슬라이스"]');
                    if (!sliceSlider) return;
                    
                    const currentValue = parseInt(sliceSlider.value);
                    const maxValue = parseInt(sliceSlider.max);
                    const minValue = parseInt(sliceSlider.min);
                    
                    // 휠 방향에 따라 슬라이스 변경 (위로 = 증가, 아래로 = 감소)
                    const delta = e.deltaY > 0 ? -1 : 1;
                    const newValue = Math.max(minValue, Math.min(maxValue, currentValue + delta));
                    
                    if (newValue !== currentValue) {
                        sliceSlider.value = newValue;
                        sliceSlider.dispatchEvent(new Event('input', { bubbles: true }));
                        sliceSlider.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }, { passive: false });
                
            }, 1000);
        }
        """,
        css="""
        .login-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100svw;
            height: 100svh;
            max-height: 100svh;
            padding: 0;
            margin: 0;
        }
        .login-wrap {
            display: flex;
            width: 100%;
            max-width: 28rem;
            height: min-content;
            max-height: fit-content;
        }
        .login-header {
            width: 100%;
        }
        .login-box {
            width: 100%;
        }
        .login-btn {
            width: 100%;
            height: 3.5rem;
        }
        .error-msg {
            padding: 0 0.75rem;
        }
            
        .viewer-container {
            width: 100svw;
            height: 100svh;
            max-height: 100svh;
            padding: 0;
            margin: 0;
            gap: 0 !important;
        }
        .inspector-container {
            padding: 1rem;
            border-bottom: 1px solid #e5e7eb;
        }
        /* 환자 목록 사이드바 스타일 */
        .patient-sidebar {
            height: 100%;
            min-height: calc(100svh - 4.225rem);
            max-height: calc(100svh - 4.225rem);
            border-right: 1px solid #e5e7eb;
            padding: 1rem;
            gap: .5rem !important;
            overflow: hidden !important;
            display: flex !important;
            flex-direction: column !important;
        }
        
        .patient-sidebar > h3 {
            flex-shrink: 0 !important;
        }
        
        .patient-sidebar > fieldset {
            border-width: 1px !important;
            border: 1px solid #d1d5db !important;
            border-radius: 0.375rem !important;
        }
        /* 스크롤바 스타일 */
        .patient-sidebar::-webkit-scrollbar {
            width: 8px;
        }
        .patient-sidebar::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        .patient-sidebar::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        .patient-sidebar::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        /* 환자 목록 Radio 스타일 - 수직 방향으로 한 줄씩 표시 */
        .patient-sidebar .wrap {
            display: flex !important;
            flex-direction: column !important;
            width: 100% !important;
        }
        .patient-sidebar label {
            width: 100% !important;
            max-width: 100% !important;
            display: flex !important;
            margin: 0.25rem 0 !important;
        }
        .patient-sidebar input[type="radio"] {
            margin-right: 0.5rem !important;
        }
        
        .patient-list {
            flex: 1 1 auto !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 100% !important;
            overflow: hidden !important;
            display: flex !important;
            flex-direction: column !important;
        }
        
        .patient-list > .wrap {
            flex: 1 1 auto !important;
            height: 100% !important;
            max-height: 100% !important;
            background-color: #ffffff !important;
            gap: 0 !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            display: flex !important;
            flex-direction: column !important;
            flex-wrap: nowrap !important;
        }
        
        .patient-list > .wrap > label {
            margin: 0 !important;
            padding: 0.75rem 0.5rem 0.75rem 0.75rem !important;
            background-color: #ffffff !important;
            border-radius: 0 !important;
            border-bottom: 1px solid #d1d5db !important;
        }
        
        .patient-list > .wrap > label:hover {
            background-color: var(--button-secondary-background-fill) !important;
        }
        
        .patient-list > .wrap > label > input[type="radio"] {
            background-color: var(--button-secondary-background-fill-hover) !important;
        }
        
        .patient-list > .wrap > label > input[type="radio"]:checked {
            background-color: var(--button-primary-background-fill) !important;
        }
        
        .patient-list > .wrap > label > span {
            margin-left: 0 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
        }
        
        .main-content-container {
            padding: 0;
            gap: 0 !important;
        }
        
        .image-display-container {
            flex-grow: 0 !important;
            height: calc(100svh - 23rem);
            max-height: calc(100svh - 23rem);
            padding: 1rem;
            border-top: 1px solid #e5e7eb;
            border-bottom: 1px solid #e5e7eb;
            user-select: none;
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
        }
        
        /* CT 이미지 배경 검정색 설정 */
        .image-display {
            padding: 1rem;
            height: 100%;
            background-color: #000 !important;
            border-radius: 0.375rem !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            overflow: hidden !important;
        }
        .image-display > div {
            width: 100%;
            height: 100%;
            background-color: #000 !important;
        }
        #ct-canvas {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            background-color: #000 !important;
        }
        .result-submission-container {
            display: flex;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: space-between !important;
            border-bottom: 1px solid #e5e7eb !important;
            padding: 0.5rem 1rem !important;
        }
        .result-radio-container {
            display: inline-box !important;
            min-width: fit-content !important;
            width: 100%;
            align-items: center;
            justify-content: flex-end;
        }
        .result-radio {
            max-width: fit-content;
        }
        .submit-btn {
            padding: 0.75rem 1.5rem;
            max-width: 10rem;
            max-height: fit-content;
        }
        
        .result_info_text {
            display: inline-block !important;
            text-align: right !important;
            color: #9ca3af !important; /* 더 연한 회색 텍스트 컬러 */
            font-size: 0.875rem !important; /* 텍스트 크기 */
            height: 2rem !important;
            max-height: 2rem !important;
        }
        
        .number-input {
            width: 4rem;
            max-width: 4rem;
        }
        
        .controls-container {
            padding: 1rem;
            border-bottom: 1px solid #e5e7eb;
        }
        
        .text-box {
            padding: 1rem;
            border-bottom: 1px solid #e5e7eb;
        }
        
        .no-padding {
            padding: 0 !important;
        }
        
        .no-gap {
            gap: 0 !important;
        }
        
        .no-margin {
            margin: 0 !important;
        }
        
        .no-flex {
            flex: none !important;
        }
        
        .fit-width {
            width: fit-content !important;
            max-width: fit-content !important;
        }
        
        .text-align-right {
            text-align: right !important;
        }
        
        .right-main-content-container {
            gap: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            height: 100%;
        }
        
        h3, p {
            margin: 0.25rem 0 !important;
        }
        
        footer {
            visibility: hidden;
        }
        
        .gradio-container {
            min-width: 100svw !important;
            min-height: 100svh !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        html, body {
            min-width: 1024px;
            min-hegiht: 924px;
            max-height: 100svh;
            overflow: hidden;
        }
        
        /* CT 이미지 업데이트 시 로딩 애니메이션 및 딤드 비활성화 */
        .image-display > div.wrap.center.full {
            display: none !important;
        }
        
        /* HTML 컴포넌트 업데이트 시 딤드 효과 제거 */
        .image-display > div.pending {
            opacity: 1 !important;
        }
        """
    ) as app:        
        # 로그인 페이지
        with gr.Column(visible=True, elem_classes="login-container") as login_page:
            with gr.Column(elem_classes="login-wrap"):
                gr.Markdown("## 검사자 정보", elem_classes="login-header")
                
                with gr.Group(elem_classes="login-box"): 
                    affiliation_input = gr.Textbox(
                        label="소속",
                        placeholder="예: 강동경희대병원 호흡기알레르기내과",
                        value="동국대학교",
                        max_lines=1
                    )
                    name_input = gr.Textbox(
                        label="성함",
                        placeholder="예: 홍길동",
                        value="김현수",
                        max_lines=1
                    )
                    password_input = gr.Textbox(
                        label="비밀번호",
                        type="password",
                        placeholder="비밀번호를 입력하세요",
                        value="dgu-plass-ct"
                    )

                    error_msg = gr.Markdown("", elem_classes="error-msg", visible=True)

                    login_btn = gr.Button("접속", variant="primary", size="lg", elem_classes="login-btn")
            
        # 뷰어 페이지
        with gr.Column(visible=False, elem_classes="viewer-container") as viewer_page:
            
            # 상단 헤더
            with gr.Row(elem_classes="inspector-container"):
                inspector_info = gr.Markdown("", elem_id="inspector-info")
                with gr.Column(scale=0, min_width=100):
                    logout_btn = gr.Button("로그아웃", size="sm", variant="secondary")
            
            # 메인 컨텐츠 영역 (사이드바 + 메인)
            with gr.Row(elem_classes="main-content-container"):
                # 좌측 사이드바 - 환자 목록
                with gr.Column(scale=1, elem_classes="patient-sidebar"):
                    gr.Markdown("### 환자 목록")
                    patient_list = gr.Radio(
                        elem_classes="patient-list",
                        choices=[],
                        label="",
                        show_label=False,
                        interactive=True,
                        container=False
                    )
                
                # 우측 메인 영역
                with gr.Column(scale=5, elem_classes="right-main-content-container"):
                    # 결과 제출부
                    
                    with gr.Row(elem_classes="result-submission-container"):
                        gr.Markdown("### 분석 결과", elem_classes="no-margin fit-width")
                        with gr.Row(elem_classes="result-radio-container"):
                            result_info_text = gr.Markdown(" ", elem_classes="result_info_text")
                            result_radio = gr.Radio(
                                elem_classes="result-radio",
                                choices=["CECT", "sCECT"],
                                show_label=False,
                                value=None,
                                container=False
                            )
                            submit_btn = gr.Button("결과 제출", variant="primary", size="sm", elem_classes="submit-btn", interactive=False)

                    submit_msg = gr.Markdown("좌측 환자 목록에서 환자를 선택한 후 결과를 제출하세요.", elem_classes="text-box")

                    # 영상 표시부
                    with gr.Column(elem_classes="image-display-container"):
                        # Canvas를 포함한 HTML 컴포넌트
                        ct_image = create_safe_html(
                            value='<canvas id="ct-canvas" width="512" height="512" style="background-color: #000;"></canvas>',
                            elem_classes="image-display",
                            label="",
                            show_label=False,
                            sanitize_html=False
                        )
                    
                    # 조절부
                    with gr.Column(elem_classes="controls-container"):
                        # 슬라이스 조절
                        with gr.Row():
                            slice_slider = gr.Slider(
                                minimum=0,
                                maximum=100,
                                value=0,
                                step=1,
                                label="슬라이스 (Slice)",
                                interactive=True,
                                scale=4
                            )
                            slice_number = gr.Number(
                                elem_classes="number-input",
                                value=0,
                                label="",
                                precision=0,
                                scale=1,
                                visible=False
                            )
                        
                        with gr.Row():
                            # 윈도우 레벨
                            with gr.Column():
                                with gr.Row():
                                    level_slider = gr.Slider(
                                        minimum=-1000,
                                        maximum=1000,
                                        value=40,
                                        step=1,
                                        label="윈도우 레벨 (Window Level, WL)",
                                        scale=3
                                    )
                                    level_number = gr.Number(
                                        elem_classes="number-input",
                                        value=40,
                                        label="",
                                        scale=1,
                                        visible=False
                                    )
                            
                            # 윈도우 너비
                            with gr.Column():
                                with gr.Row():
                                    width_slider = gr.Slider(
                                        minimum=1,
                                        maximum=2000,
                                        value=400,
                                        step=1,
                                        label="윈도우 너비 (Window Width, WW)",
                                        scale=3
                                    )
                                    width_number = gr.Number(
                                        elem_classes="number-input",
                                        value=400,
                                        label="",
                                        scale=1,
                                        visible=False
                                    )
        
        # 이벤트 핸들러 연결
        
        # 로그인
        login_btn.click(
            fn=handle_login,
            inputs=[affiliation_input, name_input, password_input],
            outputs=[login_page, viewer_page, error_msg, patient_list, inspector_info]
        )
        
        # 로그아웃
        logout_btn.click(
            fn=handle_logout,
            inputs=[],
            outputs=[
                login_page, viewer_page,
                affiliation_input, name_input, password_input,
                error_msg
            ]
        )
        
        # 환자 선택
        patient_list.change(
            fn=handle_patient_select,
            inputs=[patient_list],
            outputs=[
                ct_image,
                submit_msg,
                slice_slider, slice_number,
                level_slider, width_slider,
                result_radio, result_info_text,
                submit_btn  # 제출 버튼 상태 추가
            ]
        )
        
        # 결과 라디오 변경 시 제출 버튼 활성화/비활성화
        result_radio.change(
            fn=handle_result_radio_change,
            inputs=[result_radio],
            outputs=[submit_btn]
        )
        
        # 슬라이스 조절
        # change 이벤트: 즉시 반영 (휠 제스처 지원)
        slice_slider.change(
            fn=update_slice_from_slider,
            inputs=[slice_slider],
            outputs=[ct_image, slice_number]
        )
        
        # 숫자 입력은 change 이벤트 사용 (즉시 반영)
        slice_number.submit(
            fn=update_slice_from_number,
            inputs=[slice_number],
            outputs=[ct_image, slice_slider, slice_number]
        )
        
        # 윈도우 레벨 조절
        # change 이벤트: 즉시 반영 (드래그 중에도 업데이트)
        level_slider.change(
            fn=update_window_level,
            inputs=[level_slider],
            outputs=[ct_image, level_number]
        )
        
        # 숫자 입력은 submit 이벤트 사용 (엔터키 또는 포커스 아웃)
        level_number.submit(
            fn=update_window_level,
            inputs=[level_number],
            outputs=[ct_image, level_slider]
        )
        
        # 윈도우 너비 조절
        # change 이벤트: 즉시 반영 (드래그 중에도 업데이트)
        width_slider.change(
            fn=update_window_width,
            inputs=[width_slider],
            outputs=[ct_image, width_number]
        )
        
        # 숫자 입력은 submit 이벤트 사용 (엔터키 또는 포커스 아웃)
        width_number.submit(
            fn=update_window_width,
            inputs=[width_number],
            outputs=[ct_image, width_slider]
        )
        
        # 결과 제출
        submit_btn.click(
            fn=submit_analysis_result,
            inputs=[result_radio],
            outputs=[submit_msg, patient_list, result_info_text]
        )
    
    return app


if __name__ == "__main__":
    from config import config
    
    # 필요한 디렉토리 생성
    config.ensure_directories()
    
    # UI 생성 및 실행
    app = create_ui()
    app.launch(
        server_name=config.HOST,
        server_port=config.PORT,
        share=False
    )
