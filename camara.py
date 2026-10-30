import cv2
import urllib.request
import urllib.error
import threading
import time

try:
    from mediapipe.python.solutions import hands as mp_hands
    from mediapipe.python.solutions import drawing_utils as mp_drawing
    from mediapipe.python.solutions import drawing_styles as mp_drawing_styles
except ImportError:
    import mediapipe as mp
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

ESP32_IP = "192.168.4.1"
URL_BASE = f"http://{ESP32_IP}/control"

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=1,
    min_detection_confidence=0.75,
    min_tracking_confidence=0.65
)

cap = cv2.VideoCapture(1)

estado_focos = [0, 0, 0, 0, 0]
ultimo_gesto_enviado = -1
gesto_candidato = -1
tiempo_deteccion_candidato = 0.0
TIEMPO_ESTABILIDAD = 0.25 

texto_red = "Listo (Esperando gesto)"
color_red = (200, 200, 200)
enviando_datos = False


def tarea_http_asincrona(cantidad_dedos):
    """Envía la orden al ESP32 en segundo plano sin congelar la cámara."""
    global texto_red, color_red, estado_focos, enviando_datos
    enviando_datos = True

    url = f"{URL_BASE}?count={cantidad_dedos}"

    try:
        t0 = time.time()
        with urllib.request.urlopen(url, timeout=0.40) as resp:
            latencia = int((time.time() - t0) * 1000)
            if resp.status == 200:
                for i in range(5):
                    estado_focos[i] = 1 if i < cantidad_dedos else 0

                if cantidad_dedos == 0:
                    texto_red = f"Todos OFF | HTTP 200 ({latencia} ms)"
                else:
                    texto_red = f"Focos 1..{cantidad_dedos} ON | HTTP 200 ({latencia} ms)"
                color_red = (0, 255, 0)
            else:
                texto_red = f"Error HTTP {resp.status}"
                color_red = (0, 0, 255)
    except urllib.error.URLError as e:
        if "timed out" in str(e.reason):
            texto_red = "Error: Timeout (Revisa Wi-Fi ESP32_Luminarias)"
        else:
            texto_red = "Error: No responde ESP32 (192.168.4.1)"
        color_red = (0, 0, 255)
    except Exception:
        texto_red = "Error de conexion Wi-Fi"
        color_red = (0, 0, 255)
    finally:
        enviando_datos = False


def disparar_orden_wifi(cantidad_dedos):
    """Lanza un hilo independiente para no bloquear los FPS de OpenCV."""
    if not enviando_datos:
        hilo = threading.Thread(target=tarea_http_asincrona, args=(cantidad_dedos,), daemon=True)
        hilo.start()


def contar_dedos(landmarks):
    """
    Cuenta los dedos levantados (0 a 5) de forma independiente a si es mano
    izquierda o derecha y sin fallar por el efecto espejo (cv2.flip).
    """
    dedos = 0

    distancia_punta_pulgar = abs(landmarks[4].x - landmarks[17].x)
    distancia_nudillo_pulgar = abs(landmarks[3].x - landmarks[17].x)
    if distancia_punta_pulgar > distancia_nudillo_pulgar:
        dedos += 1

    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    for tip, pip in zip(tips, pips):
        if landmarks[tip].y < landmarks[pip].y:
            dedos += 1

    return dedos


while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1) 
    h, w, _ = frame.shape
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resultados = hands.process(frame_rgb)

    gesto_frame = -1
    etiqueta_gesto = "Esperando mano..."
    progreso_estabilidad = 0.0

    if resultados.multi_hand_landmarks:
        for hand_landmarks in resultados.multi_hand_landmarks:
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style()
            )

            n_dedos = contar_dedos(hand_landmarks.landmark)
            gesto_frame = n_dedos

            if n_dedos == 0:
                etiqueta_gesto = "PUNO (0) -> Apagar Todos"
            else:
                etiqueta_gesto = f"{n_dedos} DEDO(S) -> Encender {n_dedos} Foco(s)"

    if gesto_frame != -1:
        if gesto_frame != gesto_candidato:
            gesto_candidato = gesto_frame
            tiempo_deteccion_candidato = time.time()
        else:
            tiempo_transcurrido = time.time() - tiempo_deteccion_candidato
            progreso_estabilidad = min(tiempo_transcurrido / TIEMPO_ESTABILIDAD, 1.0)

            if tiempo_transcurrido >= TIEMPO_ESTABILIDAD:
                if gesto_candidato != ultimo_gesto_enviado and not enviando_datos:
                    ultimo_gesto_enviado = gesto_candidato
                    disparar_orden_wifi(ultimo_gesto_enviado)
    else:
        gesto_candidato = -1

    panel = frame.copy()
    cv2.rectangle(panel, (10, 10), (w - 10, 145), (25, 25, 25), -1)
    cv2.addWeighted(panel, 0.75, frame, 0.25, 0, frame)

    cv2.putText(frame, f"Gesto: {etiqueta_gesto}", (25, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.70, (0, 255, 255), 2)
    cv2.putText(frame, f"Wi-Fi: {texto_red}", (25, 72),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, color_red, 2)

    ancho_barra = int((w - 50) * progreso_estabilidad)
    cv2.rectangle(frame, (25, 82), (w - 25, 88), (60, 60, 60), -1)
    cv2.rectangle(frame, (25, 82), (25 + ancho_barra, 88), (0, 255, 255), -1)

    for i in range(5):
        x = 25 + (i * 120)
        c_fondo = (0, 180, 0) if estado_focos[i] == 1 else (55, 55, 55)
        cv2.rectangle(frame, (x, 98), (x + 105, 132), c_fondo, -1)
        cv2.rectangle(frame, (x, 98), (x + 105, 132), (220, 220, 220), 1)
        estado_txt = "ON" if estado_focos[i] == 1 else "OFF"
        cv2.putText(frame, f"Foco {i + 1}: {estado_txt}", (x + 10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    cv2.imshow("Automatizacion Residencial - Deteccion de Gestos", frame)
    if cv2.waitKey(5) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
