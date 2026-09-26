import serial
import time
import subprocess

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess


# ============================
# 設定
# ============================

COM_PORT = "COM5"
BAUD_RATE = 115200

SAMPLE_RATE = 16000
RECORD_SECONDS = 3

TEMP_AUDIO_FILE = r"D:\IOT_class\work_0917\ameba_mic.wav"


# ============================
# 連接 AMB82-mini
# ============================

try:
    ser = serial.Serial(
        COM_PORT,
        BAUD_RATE,
        timeout=1
    )

    print(f"Connected to {COM_PORT}")

except serial.SerialException:
    print("Communication disconnected")
    ser = None


# ============================
# LED 指令
# ============================

signal_dict = {
    "left": b"LEFT\n",
    "right": b"RIGHT\n",
    "off": b"OFF\n",
    "blink": b"Blink\n",
}


# ============================
# 檢查 Serial 是否還存在
# ============================

def serial_connected():

    if ser is None:
        return False

    if not ser.is_open:
        return False

    try:
        # 強制向 Windows 查詢 COM 狀態
        _ = ser.in_waiting
        return True

    except (serial.SerialException, OSError):
        return False


# ============================
# 傳送 LED 狀態
# ============================

def new_state(para_state):

    if para_state not in signal_dict:
        print("Unknown signal")
        return False

    if not serial_connected():
        print("Communication disconnected")
        return False

    try:
        print(f"Send: {para_state}")

        ser.write(
            signal_dict[para_state]
        )

        # 等待資料真正送出去
        ser.flush()

        time.sleep(0.2)

        return True

    except (serial.SerialException, OSError):
        print("Communication disconnected")
        return False


# ============================
# SenseVoice 模型
# ============================

print("Loading SenseVoice model...")

model = AutoModel(
    model="FunAudioLLM/SenseVoiceSmall",
    trust_remote_code=True,
    device="cpu",
    hub="hf"
)

print("SenseVoice loaded")


# ============================
# 語音辨識
# ============================

def recog(audio_file):

    res = model.generate(
        input=audio_file,
        cache={},
        language="auto",
        use_itn=True,
        batch_size=64
    )

    text = rich_transcription_postprocess(
        res[0]["text"]
    )

    return text


# ============================
# 等待 AMB82 傳 RTSP URL
# ============================

def get_rtsp_url():

    if not serial_connected():
        print("Communication disconnected")
        return None

    print("Waiting for AMB82-mini...")

    while True:

        if not serial_connected():
            print("Communication disconnected")
            return None

        try:
            line = ser.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

        except (serial.SerialException, OSError):
            print("Communication disconnected")
            return None

        if line:
            print("AMB82:", line)

        if line.startswith("RTSP_URL="):

            rtsp_url = line.replace(
                "RTSP_URL=",
                "",
                1
            ).strip()

            print("Audio stream:", rtsp_url)

            return rtsp_url


# ============================
# 從 AMB82 麥克風錄音
# ============================
"""
def record_from_ameba(rtsp_url):

    print()
    print("Listening...")

    command = [
        "ffmpeg",

        "-loglevel",
        "quiet",

        # 如果你的 RTSP 需要 TCP，可以解除下面兩行註解
        # "-rtsp_transport",
        # "tcp",

        "-i",
        rtsp_url,

        "-t",
        str(RECORD_SECONDS),

        "-vn",

        "-ac",
        "1",

        "-ar",
        str(SAMPLE_RATE),

        "-acodec",
        "pcm_s16le",

        "-f",
        "wav",

        "-y",

        TEMP_AUDIO_FILE
    ]

    try:
        result = subprocess.run(
            command,
            timeout=RECORD_SECONDS + 10
        )

        if result.returncode != 0:
            print("Audio receive failed")
            return None

        return TEMP_AUDIO_FILE

    except FileNotFoundError:
        print("FFmpeg not found")
        print("Please install FFmpeg first")
        return None

    except subprocess.TimeoutExpired:
        print("Audio receive timeout")
        return None
"""

def record_from_ameba(rtsp_url):
    print()
    print(f"Connecting to RTSP stream: {rtsp_url}")
    print("Listening...")

    command = [
        "ffmpeg",
        # 只顯示錯誤訊息，避免干擾但能看到報錯
        "-loglevel", "error",

        # 強制使用 TCP，避免 Wi-Fi 下 UDP 封包被擋或丟失（關鍵！）
        "-rtsp_transport", "tcp",

        # RTSP 連線逾時設定（5秒 = 5000000 微秒）
        "-stimeout", "5000000",

        "-i", rtsp_url,

        "-t", str(RECORD_SECONDS),
        "-vn",
        "-ac", "1",
        "-ar", str(SAMPLE_RATE),
        "-acodec", "pcm_s16le",
        "-f", "wav",
        "-y",
        TEMP_AUDIO_FILE
    ]

    try:
        # capture_output=True 可捕捉 FFmpeg 的錯誤輸出
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=RECORD_SECONDS + 5
        )

        if result.returncode != 0:
            print("Audio receive failed.")
            print("FFmpeg error log:\n", result.stderr)
            return None

        return TEMP_AUDIO_FILE

    except FileNotFoundError:
        print("FFmpeg not found. Please install FFmpeg and add it to PATH.")
        return None

    except subprocess.TimeoutExpired:
        print("Audio receive timeout (無法在時限內接收到音訊資料)")
        return None

# ============================
# 語音指令 -> LED
# ============================

predict_to_light = {
    "Turn off": "off",
    "Left": "left",
    "Right": "right",
    "Blink": "blink",
}


# ============================
# 判斷語音內容
# ============================

def parse_command(predict):

    clean_predict = predict.strip().rstrip(
        "。！？!?，,."
    )

    lower_predict = clean_predict.lower()

    # 左邊
    if "左边" in clean_predict:
        return predict_to_light["Left"]

    if "左邊" in clean_predict:
        return predict_to_light["Left"]

    if "left" in lower_predict:
        return predict_to_light["Left"]

    # 右邊
    if "右边" in clean_predict:
        return predict_to_light["Right"]

    if "右邊" in clean_predict:
        return predict_to_light["Right"]

    if "right" in lower_predict:
        return predict_to_light["Right"]

    # 關燈
    if "关机" in clean_predict:
        return predict_to_light["Turn off"]

    if "關機" in clean_predict:
        return predict_to_light["Turn off"]

    if "turn off" in lower_predict:
        return predict_to_light["Turn off"]

    # 閃燈
    if "闪灯" in clean_predict:
        return predict_to_light["Blink"]

    if "閃燈" in clean_predict:
        return predict_to_light["Blink"]

    if "blink" in lower_predict:
        return predict_to_light["Blink"]

    return None


# ============================
# 主程式
# ============================

try:

    # 等待 AMB82 開機
    time.sleep(2)

    # ============================
    # 先確認 Serial 還連著
    # ============================

    if not serial_connected():

        print("Communication disconnected")

    else:

        # ============================
        # 取得 RTSP URL
        # ============================

        rtsp_url = get_rtsp_url()

        if rtsp_url is None:

            print("Cannot get audio stream")

        else:

            print()
            print("======================")
            print("Voice control started")
            print("======================")

            # ============================
            # 主循環
            # ============================

            while True:

                # ========================
                # 每一輪都檢查 USB Serial
                # ========================

                if not serial_connected():

                    print()
                    print("Communication disconnected")

                    break

                # ========================
                # 從 AMB82 麥克風錄音
                # ========================

                audio_file = record_from_ameba(
                    rtsp_url
                )

                # 錄音期間有可能才拔掉 USB
                if not serial_connected():

                    print()
                    print("Communication disconnected")

                    break

                if audio_file is None:

                    print(
                        "Cannot receive audio stream"
                    )

                    time.sleep(1)

                    continue

                # ========================
                # SenseVoice 辨識
                # ========================

                try:

                    predict = recog(
                        audio_file
                    )

                except Exception as e:

                    print(
                        "Speech recognition failed:",
                        e
                    )

                    continue

                print()
                print(
                    "predict:",
                    predict
                )

                # ========================
                # 判斷指令
                # ========================

                state = parse_command(
                    predict
                )

                if state is None:

                    print(
                        "未知指令:",
                        repr(predict)
                    )

                    continue

                # ========================
                # 再次檢查 Serial
                # ========================

                if not serial_connected():

                    print()
                    print(
                        "Communication disconnected"
                    )

                    break

                # ========================
                # 傳送 LED 指令
                # ========================

                success = new_state(
                    state
                )

                if not success:

                    print(
                        "Communication disconnected"
                    )

                    break


# ============================
# Ctrl + C
# ============================

except KeyboardInterrupt:

    print()
    print("Stopping...")


# ============================
# 程式結束
# ============================

finally:

    # ============================
    # 關燈
    # ============================

    if ser is not None:

        try:

            if ser.is_open:

                try:
                    ser.write(
                        signal_dict["off"]
                    )

                    ser.flush()

                except (
                    serial.SerialException,
                    OSError
                ):
                    pass

                try:
                    ser.close()

                except Exception:
                    pass

        except Exception:
            pass

    print("Test finished")