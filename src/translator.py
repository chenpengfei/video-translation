from concurrent.futures import ThreadPoolExecutor, as_completed
from moviepy.editor import VideoFileClip
from pydub import AudioSegment

class Translator:
    def __init__(self):
        pass
        
    def extract_audio(self, video_file_path, audio_file_path):
        """
        从视频文件中提取音频轨道并保存为MP3文件。

        Args:
        - video_file_path: 视频文件的路径。
        - audio_file_path: 音频将被保存的路径（应该是.mp3格式）。
        """
        video_clip = VideoFileClip(video_file_path)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(audio_file_path)
        audio_clip.close()
        video_clip.close()

    def split_audio(self, file_path, interval=10*60*1000):  # 默认间隔改为10分钟
        """
        将指定的音频文件按照给定的时间间隔切割，并返回切割信息的列表。

        Args:
        - file_path: 音频文件的路径。
        - interval: 切割间隔，以毫秒为单位，默认为10分钟。

        Returns:
            List[Dict[str, int]]: 返回一个字典列表，每个字典包含切割后的音频文件路径、开始时间和结束时间。
        """
        # 加载音频文件
        audio = AudioSegment.from_mp3(file_path)
        
        # 计算切割次数
        duration = len(audio)  # 音频时长，单位为毫秒
        chunks = duration // interval + (1 if duration % interval else 0)

        split_info = []  # 用于存储每个切割部分的信息
        # 开始切割并保存
        for i in range(chunks):
            start = i * interval
            end = min(start + interval, duration)  # 确保不会超出音频的实际长度
            chunk = audio[start:end]
            path = f"{file_path[:-4]}_part{i+1}.mp3"
            # 将路径、开始时间、结束时间保存到字典中
            split_info.append({
                "path": path,
                "start_time": start,
                "end_time": end
            })
            chunk.export(path, format="mp3")
            print(f"Part {i+1} has been saved.")

        return split_info
    
    def format_subtitle(self, index, start_time, end_time, text):
        """
        格式化字幕条目。

        Args:
            index (int): 字幕序号。
            start_time (str): 字幕开始时间，格式为"小时:分钟:秒,毫秒"。
            end_time (str): 字幕结束时间，格式相同。
            text (str): 字幕文本。

        Returns:
            str: 格式化后的字幕内容。
        """
        
        def format(milliseconds):
            # 将毫秒转换为秒
            seconds = milliseconds // 1000
            milliseconds = milliseconds % 1000  # 剩余的毫秒
            # 将毫秒转换为秒的小数部分，并保留一位小数
            fractional_seconds = round(milliseconds / 1000, 3)  # 保留三位小数以匹配示例输出
            total_seconds = seconds + fractional_seconds
            # 将秒转换为小时、分钟和秒
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            hours = minutes // 60
            minutes = minutes % 60

            # 格式化输出，其中秒和毫秒之间用逗号隔开
            # 注意：由于total_seconds可能包含小数部分，我们分别格式化整数部分和小数部分
            formatted_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{int(milliseconds):03}"
            return formatted_time

        subtitle = f"{index}\n{format(start_time)} --> {format(end_time)}\n{text}\n\n"
        return subtitle
            
    def read_subtitle_file(self, file_path):
        """读取视频字幕文件
        
        视频字幕信息，包括字幕的序号、显示时间、字幕文本。每个字母项的格式如下：
            1. 字幕序号，表示字幕的顺序。
            2. 字幕时间戳，格式为: "开始时间 --> 结束时间"，时间格式为: "小时:分钟:秒,毫秒"。
            3. 字幕文本，可以跨越多行。
            4. 一个空行，表示字幕项的结束，同时也分隔开下一个字幕项。
            
        例如：
            1
            00:00:12,320 --> 00:00:14,080
            各位同学大家上午好
        
        Args:
            file_path (str): 字幕文件的路径

        Returns:
            List[Dict[str, str]]: 返回一个列表，列表中的每个元素是一个字典，代表一个字幕块。每个字典包含以下键值对：
                - 'index' (str): 字幕的序号。
                - 'timestamp' (str): 字幕时间戳。
                - 'text' (str): 字幕文本，原始多行文本被合并为一个字符串。
        """
        # 定义一个列表，用于存储所有的结构体（字典）
        blocks = []
        
        # 尝试打开并读取文件
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # 按空行分割内容，获取各个块
                raw_blocks = content.strip().split('\n\n')
                
                # 遍历每个块，解析并存储到列表中
                for block in raw_blocks:
                    lines = block.split('\n')
                    if len(lines) >= 3:  # 确保块有足够的行
                        block_dict = {
                            'index': lines[0],
                            'timestamp': lines[1],
                            'text': ' '.join(lines[2:]),  # 将文本行合并为一个字符串
                        }
                        blocks.append(block_dict)
                    
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except Exception as e:
            print(f"An error occurred: {e}")
            
        return blocks
    
    def translate_blocks(self, blocks, on_translate):
        """翻译字幕块列表中的文本，并将原文和翻译文本拼接，使用并发执行。
        
        Args:
            blocks (List[Dict[str, str]]): 字幕块列表。
        
        Returns:
            List[Dict[str, str]]: 翻译后的字幕块列表。
        """
        def translate_and_append(block, last_block, next_block):
            """翻译单个字幕块的文本并拼接原文与翻译文本。
            
            Args:
                block (Dict[str, str]): 单个字幕块。
            
            Returns:
                Dict[str, str]: 翻译后的字幕块。
            """
            
            original_text = block['text']
            last_text = last_block['text']
            next_text = next_block['text']
            translated_text = on_translate(original_text, last_text, next_text)  # 调用翻译方法
            # 拼接原文与翻译文本
            # block['text'] = original_text + '\n' + translated_text
            block['text'] = translated_text
            print(f"Translated: {block['text']} \n")
            return block
        
        translated_blocks = []
        last_block = blocks[0]
        next_block = blocks[0]
        for i in range(len(blocks)):
            block = blocks[i]
            if i == 0:
                last_block = block
                if len(blocks) > 1:
                    next_block = blocks[i + 1]
                else:
                    next_block = block
            elif i == len(blocks) - 1:
                last_block = blocks[i - 1]
                next_block = block
            else:
                last_block = blocks[i - 1]
                next_block = blocks[i + 1]
                
            try:
                # 直接翻译每个字幕块并添加到列表中
                translated_block = translate_and_append(block, last_block, next_block)
                translated_blocks.append(translated_block)
            except Exception as e:
                print(f"Translation error: {e}")
                
        return translated_blocks
        
    def write_subtitle_file(self, blocks, file_path):
        """将翻译后的字幕块列表保存到文件中。
        
        Args:
            blocks (List[Dict[str, str]]): 翻译后的字幕块列表。
            file_path (str): 要保存的文件路径。
        """
        with open(file_path, 'w', encoding='utf-8') as file:
            for block in blocks:
                # 写入字幕块的序号
                file.write(block['index'] + '\n')
                # 写入字幕块的时间戳
                file.write(block['timestamp'] + '\n')
                # 写入字幕块的文本，包括原文和翻译
                file.write(block['text'] + '\n')
                # 每个字幕块后面跟一个空行
                file.write('\n')
