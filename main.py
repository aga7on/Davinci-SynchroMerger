import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog, messagebox
import os

# --- Функции оптимизации дорожек ---

def _merge_clips_on_media_type(media_element, media_type_tag, progress_callback=None):
    """
    Общая функция для схлопывания клипов (видео или аудио) внутри указанного media_element.
    :param media_element: Элемент ET, который содержит <video> или <audio>
    :param media_type_tag: Тэг медиа-типа ('video' или 'audio')
    :param progress_callback: Опциональная функция для обновления прогресса GUI
    :return: (original_track_count, optimized_track_count)
    """
    media_section = media_element.find(media_type_tag)
    if media_section is None:
        print(f"Предупреждение: Секция '{media_type_tag}' не найдена. Пропускаем оптимизацию.")
        return 0, 0 # Ничего не делаем, если секции нет

    all_clips = []
    original_track_count = 0
    for track in media_section.findall('track'):
        original_track_count += 1
        for clipitem in track.findall('clipitem'):
            start_element = clipitem.find('start')
            end_element = clipitem.find('end')

            if start_element is None or end_element is None:
                # Пропускаем клипы без корректных start/end, но выводим предупреждение
                print(f"Предупреждение: Пропущен {media_type_tag} клип '{clipitem.get('name')}' без 'start' или 'end' времени.")
                continue

            clip_data = {
                'element': clipitem,
                'start': int(start_element.text),
                'end': int(end_element.text)
            }
            all_clips.append(clip_data)

    if not all_clips:
        print(f"Внимание: {media_type_tag.capitalize()} клипы для оптимизации не найдены.")
        # Удаляем старые дорожки, если нет клипов
        for track in media_section.findall('track'):
            media_section.remove(track)
        return original_track_count, 0 # Возвращаем 0 оптимизированных дорожек

    # Сортируем клипы по начальному времени
    all_clips.sort(key=lambda x: x['start'])

    optimized_tracks = [] # Список списков клипов для каждой новой дорожки

    total_clips = len(all_clips)
    processed_clips = 0

    for clip_data in all_clips:
        clip_start = clip_data['start']
        clip_end = clip_data['end']

        placed = False
        for i, track_clips_list in enumerate(optimized_tracks):
            can_place_on_this_track = True
            for existing_clip_in_track in track_clips_list:
                existing_start = existing_clip_in_track['start']
                existing_end = existing_clip_in_track['end']

                if not (clip_end <= existing_start or clip_start >= existing_end):
                    can_place_on_this_track = False
                    break

            if can_place_on_this_track:
                optimized_tracks[i].append(clip_data)
                # Сортируем клипы на дорожке, чтобы упростить последующие проверки
                optimized_tracks[i].sort(key=lambda x: x['start'])
                placed = True
                break

        if not placed:
            new_track = [clip_data]
            optimized_tracks.append(new_track)
        
        processed_clips += 1
        if progress_callback:
            progress_callback(processed_clips / total_clips * 100) # Обновление прогресса

    # Удаляем все старые дорожки из media_section
    for track in media_section.findall('track'):
        media_section.remove(track)

    # Добавляем новые оптимизированные дорожки
    for track_index, track_clips_list in enumerate(optimized_tracks):
        new_track_element = ET.SubElement(media_section, 'track')

        # Стандартные элементы enabled и locked
        enabled_elem = ET.SubElement(new_track_element, 'enabled')
        enabled_elem.text = 'TRUE'
        locked_elem = ET.SubElement(new_track_element, 'locked')
        locked_elem.text = 'FALSE'

        for clip_data in track_clips_list:
            new_track_element.append(clip_data['element'])

    return original_track_count, len(optimized_tracks)

def process_timeline(input_xml_path, output_xml_path, optimize_video, optimize_audio, progress_callback=None):
    try:
        tree = ET.parse(input_xml_path)
        root = tree.getroot()

        sequence = root.find('sequence')
        if sequence is None:
            raise ValueError("Элемент 'sequence' не найден в XML файле.")

        media = sequence.find('media')
        if media is None:
            raise ValueError("Элемент 'media' не найден в XML файле.")

        video_orig_count = 0
        video_opt_count = 0
        audio_orig_count = 0
        audio_opt_count = 0

        # Распределение прогресса: 40% на видео, 40% на аудио, 20% на сохранение/инициализацию
        base_progress = 0
        if optimize_video:
            # Прогресс для видео: от 0 до 40
            print("Оптимизация видеодорожек...")
            video_orig_count, video_opt_count = _merge_clips_on_media_type(media, 'video', lambda p: progress_callback(base_progress + p * 0.4))
            base_progress += 40
            print(f"Видео: Оригинальных дорожек: {video_orig_count}, Оптимизированных: {video_opt_count}")

        if optimize_audio:
            # Прогресс для аудио: от 40 (или 0, если видео не оптимизируется) до 80 (или 40)
            print("Оптимизация аудиодорожек...")
            audio_orig_count, audio_opt_count = _merge_clips_on_media_type(media, 'audio', lambda p: progress_callback(base_progress + p * 0.4))
            base_progress += 40
            print(f"Аудио: Оригинальных дорожек: {audio_orig_count}, Оптимизированных: {audio_opt_count}")
        
        # Оставшийся прогресс (до 100) на запись файла
        if progress_callback: progress_callback(90) # Почти завершено перед записью
        tree.write(output_xml_path, encoding='UTF-8', xml_declaration=True)
        if progress_callback: progress_callback(100) # Полное завершение

        return {
            'video_original': video_orig_count,
            'video_optimized': video_opt_count,
            'audio_original': audio_orig_count,
            'audio_optimized': audio_opt_count
        }

    except Exception as e:
        # Убедиться, что прогресс-бар сбрасывается при ошибке
        if progress_callback: progress_callback(0) 
        raise Exception(f"Ошибка при обработке XML: {e}")

# --- GUI часть ---

def browse_input_file():
    filename = filedialog.askopenfilename(
        title="Выберите входной XML файл DaVinci Resolve",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )
    if filename:
        input_entry.delete(0, tk.END)
        input_entry.insert(0, filename)
        dir_name, base_name = os.path.split(filename)
        name_without_ext, ext = os.path.splitext(base_name)
        output_entry.delete(0, tk.END)
        output_entry.insert(0, os.path.join(dir_name, f"{name_without_ext}_optimized{ext}"))

def browse_output_file():
    filename = filedialog.asksaveasfilename(
        title="Сохранить оптимизированный XML как...",
        defaultextension=".xml",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )
    if filename:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, filename)

def update_progress(percentage):
    # Теперь используем set() для установки значения tk.Scale
    progress_bar.set(percentage)
    root.update_idletasks() # Обновить GUI немедленно

def run_merge():
    input_path = input_entry.get()
    output_path = output_entry.get()

    optimize_video = video_checkbox_var.get()
    optimize_audio = audio_checkbox_var.get()

    if not input_path:
        messagebox.showerror("Ошибка", "Пожалуйста, выберите входной XML файл.")
        return
    if not output_path:
        messagebox.showerror("Ошибка", "Пожалуйста, укажите путь для сохранения выходного XML файла.")
        return
    if not os.path.exists(input_path):
        messagebox.showerror("Ошибка", f"Входной файл не найден: {input_path}")
        return
    if not optimize_video and not optimize_audio:
        messagebox.showwarning("Предупреждение", "Не выбраны типы дорожек для оптимизации (видео или аудио).")
        return

    # Сброс прогресс-бара перед началом операции
    update_progress(0)

    try:
        results = process_timeline(input_path, output_path, optimize_video, optimize_audio, update_progress)
        
        message_text = f"Таймлайн успешно оптимизирован и сохранен в:\n{output_path}\n\n"
        if optimize_video:
            message_text += f"Видео: Оригинальных дорожек: {results['video_original']}, Оптимизированных: {results['video_optimized']}\n"
        if optimize_audio:
            message_text += f"Аудио: Оригинальных дорожек: {results['audio_original']}, Оптимизированных: {results['audio_optimized']}\n"
        
        messagebox.showinfo("Успех", message_text)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Произошла ошибка при оптимизации таймлайна:\n{e}")
    finally:
        # Сбросить прогресс-бар после завершения или ошибки
        update_progress(0)

# --- Инициализация GUI ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("DaVinci Resolve Timeline Optimizer")

    # Переменные для чекбоксов
    video_checkbox_var = tk.BooleanVar(value=True) # По умолчанию включено
    audio_checkbox_var = tk.BooleanVar(value=True) # По умолчанию включено

    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(padx=10, pady=10)

    # Входной файл
    input_label = tk.Label(frame, text="Входной XML файл:")
    input_label.grid(row=0, column=0, sticky="w", pady=5)
    input_entry = tk.Entry(frame, width=60)
    input_entry.grid(row=0, column=1, pady=5)
    input_button = tk.Button(frame, text="Обзор...", command=browse_input_file)
    input_button.grid(row=0, column=2, padx=5, pady=5)

    # Выходной файл
    output_label = tk.Label(frame, text="Выходной XML файл:")
    output_label.grid(row=1, column=0, sticky="w", pady=5)
    output_entry = tk.Entry(frame, width=60)
    output_entry.grid(row=1, column=1, pady=5)
    output_button = tk.Button(frame, text="Сохранить как...", command=browse_output_file)
    output_button.grid(row=1, column=2, padx=5, pady=5)

    # Чекбоксы для выбора типа медиа
    options_frame = tk.LabelFrame(frame, text="Оптимизировать", padx=10, pady=5)
    options_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)

    video_checkbox = tk.Checkbutton(options_frame, text="Видео дорожки", variable=video_checkbox_var)
    video_checkbox.pack(anchor="w")

    audio_checkbox = tk.Checkbutton(options_frame, text="Аудио дорожки", variable=audio_checkbox_var)
    audio_checkbox.pack(anchor="w")

    # Прогресс-бар
    progress_label = tk.Label(frame, text="Прогресс:")
    progress_label.grid(row=3, column=0, sticky="w", pady=5)
    # Удален state='disabled', так как мы хотим его обновлять
    progress_bar = tk.Scale(frame, from_=0, to=100, orient=tk.HORIZONTAL, length=400, showvalue=0) 
    progress_bar.grid(row=3, column=1, columnspan=2, sticky="ew", pady=5)


    # Кнопка запуска
    merge_button = tk.Button(frame, text="Оптимизировать таймлайн", command=run_merge,
                             font=('Arial', 10, 'bold'), bg='#4CAF50', fg='white', relief=tk.RAISED, bd=3)
    merge_button.grid(row=4, column=0, columnspan=3, pady=20)

    # Запускаем основной цикл GUI
    root.mainloop()