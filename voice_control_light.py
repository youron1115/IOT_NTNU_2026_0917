import os
import time
import serial
import sounddevice as sd
import scipy.io.wavfile as wav

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

# ============================
# 設定
# ============================

COM_PORT = "COM5"
BAUD_RATE = 115200

SAMPLE_RATE = 16000
RECORD_SECONDS = 3

TEMP_AUDIO_FILE = r"D:\IOT_class\work_0917\pc_mic.wav"
os.makedirs(os.path.dirname(TEMP_AUDIO_FILE), exist_ok=True)

# ============================
# 連線 AMB82-mini
# ============================

try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to {COM_PORT}")
except serial.SerialException as e:
    print(f"Communication disconnected: {e}")
    ser = None

# ============================
# LED 控制指令
# 必須對應 AMB82 程式中的字串
# ============================

signal_dict = {
    "left": b"LEFT\n",
    "right": b"RIGHT\n",
    "off": b"OFF\n",
    "blink": b"Blink\n",
}


def serial_connected():
    if ser is None or not ser.is_open:
        return False

    try:
        _ = ser.in_waiting
        return True
    except (serial.SerialException, OSError):
        return False


def new_state(para_state):
    if para_state not in signal_dict:
        print("Unknown signal")
        return False

    if not serial_connected():
        print("Communication disconnected")
        return False

    try:
        print(f"Send: {para_state}")
        ser.write(signal_dict[para_state])
        ser.flush()
        time.sleep(0.2)
        return True
    except (serial.SerialException, OSError):
        print("Communication disconnected")
        return False


# ============================
# 電腦麥克風錄音
# ============================

def record_from_pc():
    print()
    print("Listening (Speak to PC microphone)...")

    try:
        audio_data = sd.rec(
            int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16"
        )
        sd.wait()
        wav.write(TEMP_AUDIO_FILE, SAMPLE_RATE, audio_data)
        return TEMP_AUDIO_FILE

    except Exception as e:
        print("Audio recording failed:", e)
        return None


# ============================
# SenseVoice 語音辨識
# ============================

print("Loading SenseVoice model...")

model = AutoModel(
    model="FunAudioLLM/SenseVoiceSmall",
    trust_remote_code=True,
    device="cpu",
    hub="hf"
)

print("SenseVoice loaded")


def recog(audio_file):
    res = model.generate(
        input=audio_file,
        cache={},
        language="auto",
        use_itn=True,
        batch_size=64
    )
    text = rich_transcription_postprocess(res[0]["text"])
    return text


# ============================
# 語音指令判斷
# ============================

predict_to_light = {
    "Turn off": "off",
    "Left": "left",
    "Right": "right",
    "Blink": "blink",
}


def parse_command(predict):
    clean_predict = predict.strip().rstrip("。！，、,.!?")
    lower_predict = clean_predict.lower()

    # 左燈
    if any(k in clean_predict for k in ["左边"]):
        return predict_to_light["Left"]
    if "left" in lower_predict:
        return predict_to_light["Left"]

    # 右燈
    if any(k in clean_predict for k in ["右边"]):
        return predict_to_light["Right"]
    if "right" in lower_predict:
        return predict_to_light["Right"]

    # 關燈
    if any(k in clean_predict for k in ["关机"]):
        return predict_to_light["Turn off"]
    if "turn off" in lower_predict or "Turn off" in lower_predict:
        return predict_to_light["Turn off"]

    # 閃爍
    if any(k in clean_predict for k in ["闪灯"]):
        return predict_to_light["Blink"]
    if "blink" in lower_predict:
        return predict_to_light["Blink"]

    return None


# ============================
# 主程式
# ============================

try:
    if not serial_connected():
        print("Communication disconnected")
    else:
        print()
        print("======================")
        print("Voice control started")
        print("======================")

        while True:
            if not serial_connected():
                print("\nCommunication disconnected")
                break

            # 1. 錄音
            audio_file = record_from_pc()
            if audio_file is None:
                time.sleep(1)
                continue

            # 2. 語音辨識
            try:
                predict = recog(audio_file)
            except Exception as e:
                print("Speech recognition failed:", e)
                continue

            print()
            print("predict:", predict)

            # 3. 轉換為 LED 指令
            state = parse_command(predict)
            if state is None:
                print("Unknown command:", repr(predict))
                continue

            # 4. 傳送給 AMB82 LED
            if not new_state(state):
                break

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    if ser is not None and ser.is_open:
        try:
            ser.write(signal_dict["off"])
            ser.flush()
            ser.close()
        except Exception:
            pass

    print("Test finished")