from pathlib import Path
from os import makedirs
from datetime import datetime
from enum import Enum

from ffmpy import FFmpeg
from telegram import File


class ConversionPairs(Enum):
    jpg_to_png = (".jpg", ".png")
    png_to_jpg = (".png", '.jpg')
    
    jpeg_to_png = (".jpeg", ".png")
    png_to_jpeg = (".png", ".jpeg")
    
    #webm_to_mp4 = (".webm", ".mp4")
    #mp4_to_webm = ("mp4", ".webm")
    
    

class Converter:
    def __init__(self, conversion_pair: tuple[str, str]) -> None:
        
        self.in_t: str = conversion_pair[0]
        self.out_t: str = conversion_pair[1]
        
    def verify_signature(self, file: File) -> tuple[bool, str]:
        file_extension = ""
        try:
            file_extension = Path(file.file_path).suffix
            assert file_extension == self.in_t, "Wrong file extension"
            return True, file_extension
        except:
            return False, file_extension
    
    async def convert(self, file: File) -> tuple[Path, Path]:
        tmp_files = Path("tmp") / datetime.now().strftime("%d-%m-%Y-%H:%M:%S")
        makedirs(tmp_files, exist_ok=True)

        inp_file_path = tmp_files / Path(file.file_path).name
        out_file_path = inp_file_path.with_suffix(self.out_t)

        await file.download_to_drive(inp_file_path)
        
        ff = FFmpeg(
            inputs={inp_file_path: None},
            outputs={out_file_path: None},
            global_options=("-loglevel error")
        )
        
        ff.run()
        
        return inp_file_path, out_file_path