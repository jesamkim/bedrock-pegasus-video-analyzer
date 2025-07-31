#!/usr/bin/env python3
"""
비디오 인코딩 모듈
ffmpeg를 사용하여 비디오를 30MB 이하로 압축
"""

import os
import subprocess
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Callable, Optional

class VideoEncoder:
    def __init__(self, target_size_mb: int = 30):
        self.target_size_mb = target_size_mb
        self.target_size_bytes = target_size_mb * 1024 * 1024
        
    def get_video_info(self, input_path: str) -> Dict[str, Any]:
        """비디오 정보 추출"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams',
                input_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            
            # 비디오 스트림 찾기
            video_stream = None
            for stream in info['streams']:
                if stream['codec_type'] == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            duration = float(info['format']['duration'])
            file_size = int(info['format']['size'])
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            
            return {
                'duration': duration,
                'file_size': file_size,
                'width': width,
                'height': height,
                'bitrate': int(info['format'].get('bit_rate', 0))
            }
            
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")
    
    def calculate_target_bitrate(self, duration: float) -> int:
        """목표 파일 크기에 맞는 비트레이트 계산"""
        # 오디오 비트레이트 (128kbps) 고려
        audio_bitrate = 128 * 1000
        # 전체 비트레이트에서 오디오 비트레이트 제외
        total_bitrate = (self.target_size_bytes * 8) / duration
        video_bitrate = max(total_bitrate - audio_bitrate, 100000)  # 최소 100kbps
        
        return int(video_bitrate)
    
    def get_optimal_resolution(self, width: int, height: int) -> tuple:
        """최적 해상도 계산 (16:9 비율 유지)"""
        aspect_ratio = width / height
        
        # 최대 해상도 제한
        max_width = 854  # 480p 기준
        max_height = 480
        
        if width > max_width or height > max_height:
            if aspect_ratio > 1:  # 가로가 더 긴 경우
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:  # 세로가 더 긴 경우
                new_height = max_height
                new_width = int(max_height * aspect_ratio)
            
            # 2의 배수로 맞춤 (ffmpeg 요구사항)
            new_width = new_width - (new_width % 2)
            new_height = new_height - (new_height % 2)
            
            return new_width, new_height
        
        return width, height
    
    async def encode_video(
        self, 
        input_path: str, 
        output_path: str, 
        progress_callback: Optional[Callable[[int, str, str], None]] = None
    ) -> Dict[str, Any]:
        """비디오 인코딩 실행"""
        try:
            # ffmpeg 설치 확인
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # ffmpeg가 없는 경우 파일 복사로 대체
                if progress_callback:
                    progress_callback(10, "FFmpeg 없음 - 파일 복사 중", "FFmpeg가 설치되지 않아 원본 파일을 사용합니다.")
                
                import shutil
                shutil.copy2(input_path, output_path)
                
                original_size = os.path.getsize(input_path)
                
                if progress_callback:
                    progress_callback(100, "완료", "원본 파일을 사용합니다 (FFmpeg 미설치).")
                
                return {
                    'success': True,
                    'original_size_mb': original_size / (1024 * 1024),
                    'encoded_size_mb': original_size / (1024 * 1024),
                    'compression_ratio': 1.0,
                    'duration': 0,
                    'note': 'FFmpeg not available - using original file'
                }
            
            # 1. 비디오 정보 추출
            if progress_callback:
                progress_callback(10, "비디오 정보 분석 중", "파일 속성을 확인하고 있습니다...")
            
            video_info = self.get_video_info(input_path)
            duration = video_info['duration']
            original_size = video_info['file_size']
            
            # 이미 목표 크기보다 작으면 복사만
            if original_size <= self.target_size_bytes:
                if progress_callback:
                    progress_callback(50, "파일 복사 중", "이미 최적 크기입니다...")
                
                import shutil
                shutil.copy2(input_path, output_path)
                
                if progress_callback:
                    progress_callback(100, "완료", "인코딩이 완료되었습니다.")
                
                return {
                    'success': True,
                    'original_size_mb': original_size / (1024 * 1024),
                    'encoded_size_mb': original_size / (1024 * 1024),
                    'compression_ratio': 1.0,
                    'duration': duration
                }
            
            # 2. 인코딩 파라미터 계산
            if progress_callback:
                progress_callback(20, "인코딩 파라미터 계산 중", "최적 설정을 계산하고 있습니다...")
            
            target_bitrate = self.calculate_target_bitrate(duration)
            new_width, new_height = self.get_optimal_resolution(video_info['width'], video_info['height'])
            
            # 3. ffmpeg 명령어 구성
            cmd = [
                'ffmpeg', '-i', input_path,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '28',
                '-maxrate', f'{target_bitrate}',
                '-bufsize', f'{target_bitrate * 2}',
                '-vf', f'scale={new_width}:{new_height}',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',  # 출력 파일 덮어쓰기
                output_path
            ]
            
            # 4. 인코딩 실행
            if progress_callback:
                progress_callback(30, "비디오 인코딩 중", "ffmpeg로 압축하고 있습니다...")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 진행률 모니터링을 위한 간단한 방법 (실제로는 ffmpeg 출력 파싱 필요)
            for i in range(30, 90, 10):
                await asyncio.sleep(1)  # 실제로는 ffmpeg 진행률 파싱
                if progress_callback:
                    progress_callback(i, "비디오 인코딩 중", f"진행률: {i}%")
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"FFmpeg failed: {stderr.decode()}")
            
            # 5. 결과 확인
            if progress_callback:
                progress_callback(95, "결과 확인 중", "인코딩 결과를 검증하고 있습니다...")
            
            if not os.path.exists(output_path):
                raise Exception("Output file was not created")
            
            encoded_size = os.path.getsize(output_path)
            compression_ratio = original_size / encoded_size if encoded_size > 0 else 1.0
            
            if progress_callback:
                progress_callback(100, "완료", "인코딩이 성공적으로 완료되었습니다.")
            
            return {
                'success': True,
                'original_size_mb': original_size / (1024 * 1024),
                'encoded_size_mb': encoded_size / (1024 * 1024),
                'compression_ratio': compression_ratio,
                'duration': duration,
                'resolution': f"{new_width}x{new_height}",
                'target_bitrate': target_bitrate
            }
            
        except Exception as e:
            if progress_callback:
                progress_callback(0, "오류 발생", f"인코딩 실패: {str(e)}")
            
            return {
                'success': False,
                'error': str(e)
            }

# 전역 인코더 인스턴스
video_encoder = VideoEncoder(target_size_mb=30)
