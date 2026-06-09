from ursina import *
import numpy as np
import math
import os
import pygame
import shutil

# --- 1. 앱 초기화 ---
app = Ursina()
window.title = "3D Stereophonic Sound Simulator"
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# 한글 깨짐 방지 폰트
font_path = 'malgun.ttf'
sys_font = 'C:\\Windows\\Fonts\\malgun.ttf'
if not os.path.exists(font_path) and os.path.exists(sys_font):
    try:
        shutil.copy(sys_font, font_path)
    except Exception:
        pass

if os.path.exists(font_path):
    Text.default_font = font_path
else:
    font_path = None

# --- 2. 오디오 합성 및 재생 (Pygame Mixer) ---
pygame.mixer.init(frequency=44100, size=-16, channels=2)
from scipy.signal import butter, lfilter

def generate_synth_sound(freq=220.0, sample_rate=44100, duration=1.0, muffled=False):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.sin(2 * np.pi * freq * t) * 0.5
    
    if not muffled:
        wave += np.sin(2 * np.pi * (freq * 1.01) * t) * 0.25
        wave += np.sin(2 * np.pi * (freq * 2.0) * t) * 0.15
        wave += np.sin(2 * np.pi * (freq * 3.0) * t) * 0.1
    
    wave += np.sin(2 * np.pi * (freq * 0.5) * t) * 0.25
    lfo = (np.sin(2 * np.pi * 4 * t) + 1) / 2
    wave = wave * (0.5 + 0.5 * lfo)
    
    audio_data = np.int16(wave * 32767 * 0.5)
    stereo_data = np.column_stack((audio_data, audio_data))
    return pygame.sndarray.make_sound(stereo_data)

def generate_muffled_sound(sound):
    try:
        data = pygame.sndarray.array(sound)
        # 8000Hz cutoff Butterworth filter for an extremely subtle and natural rear-projection lowpass effect
        b, a = butter(2, 8000.0 / 22050.0, btype='low')
        muffled_data = lfilter(b, a, data, axis=0).astype(data.dtype)
        return pygame.sndarray.make_sound(muffled_data)
    except Exception as e:
        print("Muffling error:", e)
        return sound

custom_audio_file = None
for ext in ['.wav', '.ogg', '.mp3']:
    if os.path.exists(f'bell{ext}'):
        custom_audio_file = f'bell{ext}'
        break

channel_front = pygame.mixer.Channel(0)
channel_back = pygame.mixer.Channel(1)

# Initialize volumes to 0 to prevent loud blast during black screen loading
channel_front.set_volume(0.0, 0.0)
channel_back.set_volume(0.0, 0.0)

if custom_audio_file:
    try:
        custom_sound_front = pygame.mixer.Sound(custom_audio_file)
        custom_sound_back = generate_muffled_sound(custom_sound_front)
        channel_front.play(custom_sound_front, loops=-1)
        channel_back.play(custom_sound_back, loops=-1)
    except Exception:
        front_synth_sound = generate_synth_sound(muffled=False)
        back_synth_sound = generate_synth_sound(muffled=True)
        channel_front.play(front_synth_sound, loops=-1)
        channel_back.play(back_synth_sound, loops=-1)
else:
    front_synth_sound = generate_synth_sound(muffled=False)
    back_synth_sound = generate_synth_sound(muffled=True)
    channel_front.play(front_synth_sound, loops=-1)
    channel_back.play(back_synth_sound, loops=-1)

# --- 3. 환경 스카이박스 (실사 파노라마 전용, 모델 렌더링 없음) ---
from ursina.shaders import unlit_shader
panorama_sky = Entity(
    model='sphere',
    scale=500,
    double_sided=True,
    shader=unlit_shader,
    texture='Street View 360.jpg' if os.path.exists('Street View 360.jpg') else 'sky_default'
)
if os.path.exists('Street View 360.jpg'):
    panorama_sky.texture.filtering = 'linear'
    panorama_sky.texture_scale = (-1, 1)

# --- 4. 카메라 고정 (이동 및 스피커 제거) ---
camera.y = 2
camera.fov = 90
mouse.locked = True

# 음원 위치 고정 (원점 기준 75도 반시계 방향 위치)
sound_pos = Vec3(-3.5355, 2.3, 6.1237)

# --- 5. 사이버-글래스 HUD (UI) 구성 ---
hud_border = Entity(parent=camera.ui, model='quad', color=color.cyan, scale=(0.74, 0.46), position=(-0.48, 0.20), z=1.5)
ui_bg = Entity(parent=camera.ui, model='quad', color=color.rgba(10/255.0, 15/255.0, 25/255.0, 230/255.0), scale=(0.72, 0.44), position=(-0.48, 0.20), z=1.4)

info_text = Text(text='데이터 연산 중...', parent=camera.ui, position=(-0.81, 0.39), scale=0.95, font=font_path, color=color.white, z=1.0)

# 볼륨 바 및 트래커 UI
gl_bar_label = Text(text='좌측 볼륨', parent=camera.ui, position=(-0.80, 0.09), scale=0.9, color=color.cyan)
gl_bar_bg = Entity(parent=camera.ui, model='quad', color=color.rgba(100/255.0, 100/255.0, 100/255.0, 50/255.0), scale=(0.28, 0.015), position=(-0.64, 0.05), z=1.1)
gl_bar = Entity(parent=camera.ui, model='quad', color=color.cyan, scale=(0.0, 0.015), position=(-0.78, 0.05), origin=(-0.5, 0), z=1.0)

gr_bar_label = Text(text='우측 볼륨', parent=camera.ui, position=(-0.44, 0.09), scale=0.9, color=color.cyan)
gr_bar_bg = Entity(parent=camera.ui, model='quad', color=color.rgba(100/255.0, 100/255.0, 100/255.0, 50/255.0), scale=(0.28, 0.015), position=(-0.30, 0.05), z=1.1)
gr_bar = Entity(parent=camera.ui, model='quad', color=color.cyan, scale=(0.0, 0.015), position=(-0.44, 0.05), origin=(-0.5, 0), z=1.0)

pos_bar_label = Text(text='소리 도달 방위각 트래커 (L <----> R)', parent=camera.ui, position=(-0.80, 0.02), scale=0.9, color=color.orange)
pos_bar_bg = Entity(parent=camera.ui, model='quad', color=color.rgba(100/255.0, 100/255.0, 100/255.0, 50/255.0), scale=(0.60, 0.01), position=(-0.48, -0.01), z=1.1)
pos_bar_center = Entity(parent=camera.ui, model='quad', color=color.gray, scale=(0.005, 0.02), position=(-0.48, -0.01), z=1.0)
pos_cursor = Entity(parent=camera.ui, model='quad', color=color.orange, scale=(0.015, 0.015), position=(-0.48, -0.01), z=0.9)

crosshair = Entity(parent=camera.ui, model='quad', scale=0.01, color=color.green, z=1.0)

# --- 6. ESC 설정 메뉴 (중앙 집중) ---
pause_menu = Entity(parent=camera.ui, enabled=False, z=-10.0)
menu_bg_overlay = Entity(parent=pause_menu, model='quad', color=color.rgba(0, 0, 0, 150/255.0), scale=(2, 2), z=0.9)
menu_panel_border = Entity(parent=pause_menu, model='quad', color=color.cyan, scale=(0.52, 0.50), position=(0, 0), z=0.5)
menu_panel = Entity(parent=pause_menu, model='quad', color=color.rgba(10/255.0, 15/255.0, 25/255.0, 240/255.0), scale=(0.5, 0.48), position=(0, 0), z=0.4)

menu_title = Text(parent=pause_menu, text='설정 메뉴', origin=(0, 0), y=0.16, scale=1.5, color=color.cyan, z=0.1)

vol_label = Text(parent=pause_menu, text='마스터 볼륨', origin=(0, 0), y=0.07, scale=1.0, color=color.white, z=0.1)
vol_slider = Slider(parent=pause_menu, min=0.0, max=3.0, default=2.5, y=0.01, scale=0.6, dynamic=True, z=0.1)
vol_slider.knob.color = color.cyan
vol_slider.x = -0.15

def resume_game():
    pause_menu.enabled = False
    mouse.locked = True

resume_btn = Button(parent=pause_menu, text='돌아가기', scale=(0.3, 0.06), y=-0.08, color=color.rgba(20/255.0, 30/255.0, 45/255.0, 220/255.0), highlight_color=color.rgba(0, 255/255.0, 200/255.0, 80/255.0), z=0.1, on_click=resume_game)
exit_btn = Button(parent=pause_menu, text='종료', scale=(0.3, 0.06), y=-0.16, color=color.rgba(20/255.0, 30/255.0, 45/255.0, 220/255.0), highlight_color=color.rgba(0, 255/255.0, 200/255.0, 80/255.0), z=0.1, on_click=application.quit)

def input(key):
    if key == 'escape':
        pause_menu.enabled = not pause_menu.enabled
        mouse.locked = not pause_menu.enabled

# ITD 연산 상수
r_c = 0.00025
d = np.linalg.norm(np.array([sound_pos.x, sound_pos.y, sound_pos.z]) - np.array([camera.x, camera.y, camera.z]))
if d == 0: d = 0.0001
s_unit = (np.array([sound_pos.x, sound_pos.y, sound_pos.z]) - np.array([camera.x, camera.y, camera.z])) / d

# --- 7. 매 프레임 업데이트 루프 ---
def update():
    # 마우스 방향 전환 회전
    if mouse.locked:
        camera.rotation_y += mouse.velocity[0] * 40
        camera.rotation_x -= mouse.velocity[1] * 40
        camera.rotation_x = max(-90.0, min(90.0, camera.rotation_x))

    c_right = np.array([camera.right.x, camera.right.y, camera.right.z])
    
    # 내적 연산
    dot = np.dot(s_unit, c_right)
    dot = max(-1.0, min(1.0, dot))
    
    gr = math.sqrt((1 + dot) / 2)
    gl = math.sqrt((1 - dot) / 2)
    
    c_forward = np.array([camera.forward.x, camera.forward.y, camera.forward.z])
    c_up = np.array([camera.up.x, camera.up.y, camera.up.z])
    
    front_dot = np.dot(s_unit, c_forward)
    up_dot = np.dot(s_unit, c_up)
    
    clarity = (front_dot + 1.0) / 2.0
    
    # 상하(Elevation) 입체감 구현:
    # 소리가 위(up_dot > 0)에 있을 땐 약간 더 크고 뚜렷하게, 아래(up_dot < 0)에 있을 땐 몸통에 가려져 볼륨 감소 및 탁해짐
    elevation_attenuation = 1.0
    if up_dot < 0:
        elevation_attenuation = 1.0 + (up_dot * 0.4) # 최대 40% 감쇠
        clarity += up_dot * 0.2 # 아래쪽 소리는 조금 더 먹먹해짐
    else:
        elevation_attenuation = 1.0 + (up_dot * 0.2) # 위쪽 소리는 최대 20% 증폭
        
    clarity = max(0.0, min(1.0, clarity))
    
    # Use linear crossfade instead of equal-power (sqrt) to prevent phase-cancellation volume dips with correlated signals
    front_mix = clarity
    back_mix = 1.0 - clarity
    
    # 후방 볼륨 감쇠 (뒤에서 들려오는 소리는 전체적으로 15% 정도 볼륨을 감소시켜 앞뒤 분별력 극대화)
    back_attenuation = 1.0
    if front_dot < 0:
        back_attenuation = 1.0 + (front_dot * 0.15)
        
    # 거리 고정 (이동 안함), 감쇠 고정
    attenuation = min(1.0, 3.0 / (d + 1.0)) * elevation_attenuation * back_attenuation
    
    master_vol = vol_slider.value
    
    channel_front.set_volume(min(1.0, gl * attenuation * front_mix * master_vol), min(1.0, gr * attenuation * front_mix * master_vol))
    channel_back.set_volume(min(1.0, gl * attenuation * back_mix * master_vol), min(1.0, gr * attenuation * back_mix * master_vol))
    
    itd = r_c * ((math.pi / 2) - dot + math.sqrt(1 - dot**2))
    
    gl_bar.scale_x = gl * 0.28
    gr_bar.scale_x = gr * 0.28
    pos_cursor.x = -0.48 + dot * 0.30
    
    info_text.text = f'''<color:orange>■ 실시간 수치 데이터<default>
  • 내적 (cosθ) : {dot:.3f}

<color:green>■ 좌우 볼륨 비율<default>
  • 좌측 채널 : {gl:.2f} ({(gl**2)*100:.1f}%)  |  우측 채널 : {gr:.2f} ({(gr**2)*100:.1f}%)

<color:cyan>■ 소리 도달 시간차<default>
  • 시간차 (ITD) : {itd*1e6:.1f} ㎲ ({itd:.6f} 초)

[조작] 마우스: 회전 | ESC: 설정 메뉴'''

app.run()