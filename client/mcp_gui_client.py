#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import sys
import websockets
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Dict, Any, List
import speech_recognition as sr
import pyaudio
import wave
import tempfile
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mcp-gui-client")

# Configuration
MCP_HOST_URL = os.environ.get("MCP_HOST_URL", "ws://localhost:8765")

class AudioRecorder:
    """Simple audio recorder using PyAudio and Google Speech Recognition."""
    def __init__(self, duration=5, on_status_update=None, on_progress_update=None, on_finished=None):
        self.duration = duration
        self.is_recording = False
        self.on_status_update = on_status_update
        self.on_progress_update = on_progress_update
        self.on_finished = on_finished
        self.recognizer = sr.Recognizer()
        
    def start(self):
        """Start recording in a new thread."""
        self.is_recording = True
        threading.Thread(target=self._record, daemon=True).start()
    
    def stop(self):
        """Stop recording."""
        self.is_recording = False
    
    def _record(self):
        """Record audio and transcribe it."""
        temp_file = None
        
        try:
            if self.on_status_update:
                self.on_status_update("Initializing...")
            
            # Create a temporary file
            fd, temp_file = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            
            # Audio recording parameters
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 44100
            CHUNK = 1024
            
            # Initialize PyAudio
            audio = pyaudio.PyAudio()
            
            # Start recording
            if self.on_status_update:
                self.on_status_update("Recording... Speak now")
            
            stream = audio.open(format=FORMAT, channels=CHANNELS,
                               rate=RATE, input=True,
                               frames_per_buffer=CHUNK)
            
            frames = []
            start_time = time.time()
            
            # Record for specified duration or until stopped
            while self.is_recording and (time.time() - start_time) < self.duration:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                # Update progress
                elapsed = time.time() - start_time
                progress = min(int((elapsed / self.duration) * 100), 100)
                if self.on_progress_update:
                    self.on_progress_update(progress)
            
            # Stop recording
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            if self.on_status_update:
                self.on_status_update("Processing audio...")
            
            # Save the recorded audio to the temporary file
            with wave.open(temp_file, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            
            # Transcribe the audio
            if self.on_status_update:
                self.on_status_update("Transcribing with Google...")
            
            with sr.AudioFile(temp_file) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data)
                
                if self.on_status_update:
                    self.on_status_update("Transcription complete")
                
                if self.on_finished:
                    self.on_finished(text)
        
        except sr.UnknownValueError:
            if self.on_status_update:
                self.on_status_update("Could not understand audio")
            if self.on_finished:
                self.on_finished("")
        except sr.RequestError as e:
            if self.on_status_update:
                self.on_status_update(f"Google Speech Recognition service error: {e}")
            if self.on_finished:
                self.on_finished("")
        except Exception as e:
            logger.error(f"Error in audio recording/transcription: {str(e)}")
            if self.on_status_update:
                self.on_status_update(f"Error: {str(e)}")
            if self.on_finished:
                self.on_finished("")
        finally:
            # Clean up
            self.is_recording = False
            if self.on_progress_update:
                self.on_progress_update(0)
            
            # Delete temporary file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Could not delete temporary file: {str(e)}")

class MCPClient:
    """Client for communicating with the MCP host."""
    def __init__(self, host_url: str):
        self.host_url = host_url
        self.websocket = None
        self.message_history: List[Dict[str, Any]] = []
        
    async def connect(self):
        """Connect to the MCP host."""
        try:
            self.websocket = await websockets.connect(self.host_url)
            logger.info(f"Connected to MCP host at {self.host_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP host: {str(e)}")
            return False
    
    async def receive_message(self):
        """Receive a single message from the MCP host."""
        if not self.websocket:
            logger.error("Not connected to host")
            return None
        
        try:
            message = await self.websocket.recv()
            return json.loads(message)
        except Exception as e:
            logger.error(f"Error receiving message: {str(e)}")
            return None
    
    async def send_message(self, content: str):
        """Send a user message to the MCP host."""
        if not self.websocket:
            logger.error("Not connected to host")
            return False
        
        try:
            await self.websocket.send(json.dumps({
                "type": "user_message",
                "content": content
            }))
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False
    
    async def clear_history(self):
        """Clear the conversation history."""
        if not self.websocket:
            logger.error("Not connected to host")
            return False
        
        try:
            await self.websocket.send(json.dumps({
                "type": "clear_history"
            }))
            return True
        except Exception as e:
            logger.error(f"Failed to clear history: {str(e)}")
            return False
    
    async def close(self):
        """Close the connection to the MCP host."""
        if self.websocket:
            await self.websocket.close()
            logger.info("Connection to MCP host closed")

class MCPClientGUI:
    """GUI for the MCP client."""
    def __init__(self, root):
        self.root = root
        self.root.title("MCP Client")
        self.root.geometry("800x600")
        
        self.client = MCPClient(host_url=MCP_HOST_URL)
        self.audio_recorder = None
        self.is_connected = False
        
        self.init_ui()
        
        # Start the async loop in a separate thread
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_async_loop)
        self.loop_thread.daemon = True
        self.loop_thread.start()
    
    def init_ui(self):
        """Initialize the UI components."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Initializing...")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create a paned window
        paned_window = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Input frame
        input_frame = ttk.LabelFrame(paned_window, text="Input", padding=5)
        paned_window.add(input_frame, weight=1)
        
        # Input text area
        self.input_text = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=5)
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Button frame
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Buttons
        self.send_button = ttk.Button(button_frame, text="Send", command=self.on_send_clicked, state=tk.DISABLED)
        self.send_button.pack(side=tk.LEFT, padx=5)
        
        self.record_button = ttk.Button(button_frame, text="Record Audio", command=self.on_record_clicked, state=tk.DISABLED)
        self.record_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="Clear History", command=self.on_clear_clicked, state=tk.DISABLED)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Audio status
        audio_status_frame = ttk.Frame(input_frame)
        audio_status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(audio_status_frame, text="Audio:").pack(side=tk.LEFT, padx=5)
        self.audio_status_var = tk.StringVar(value="Ready")
        ttk.Label(audio_status_frame, textvariable=self.audio_status_var).pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(input_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Output frame
        output_frame = ttk.LabelFrame(paned_window, text="Output", padding=5)
        paned_window.add(output_frame, weight=2)
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def on_record_clicked(self):
        """Handle record button click."""
        try:
            if self.audio_recorder and self.audio_recorder.is_recording:
                self.audio_recorder.stop()
                self.record_button.config(text="Record Audio")
                self.audio_status_var.set("Processing audio...")
            else:
                self.record_button.config(text="Stop Recording")
                self.audio_status_var.set("Preparing to record...")
                
                self.audio_recorder = AudioRecorder(
                    duration=10,  # 10 seconds recording
                    on_status_update=self._update_audio_status,
                    on_progress_update=self._update_progress,
                    on_finished=self._on_transcription_finished
                )
                
                self.audio_recorder.start()
        except Exception as e:
            logger.error(f"Error in record button handler: {str(e)}")
            self.audio_status_var.set(f"Error: {str(e)}")
            self.record_button.config(text="Record Audio")
    
    def _run_async_loop(self):
        """Run the asyncio event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_and_listen())
    
    async def _connect_and_listen(self):
        """Connect to the MCP host and listen for messages."""
        success = await self.client.connect()
        
        # Update UI from the main thread
        self.root.after(0, self._update_connection_status, success)
        
        if success:
            while True:
                try:
                    message = await self.client.receive_message()
                    if message:
                        # Update UI from the main thread
                        self.root.after(0, self._handle_message, message)
                except Exception as e:
                    logger.error(f"Error in message loop: {str(e)}")
                    break
    
    def _update_connection_status(self, connected):
        """Update the UI based on connection status."""
        self.is_connected = connected
        if connected:
            self.status_var.set("Connected to MCP host")
            self.send_button.config(state=tk.NORMAL)
            self.record_button.config(state=tk.NORMAL)
            self.clear_button.config(state=tk.NORMAL)
        else:
            self.status_var.set("Failed to connect to MCP host")
    
    def _handle_message(self, message):
        """Handle received messages."""
        try:
            if message["type"] == "llm_response":
                self.output_text.config(state=tk.NORMAL)
                self.output_text.insert(tk.END, f"\n----- LLM Response for: '{message['user_message']}' -----\n")
                self.output_text.insert(tk.END, message["response"])
                self.output_text.insert(tk.END, "\n-----------------------\n")
                self.output_text.see(tk.END)
                self.output_text.config(state=tk.DISABLED)
            
            elif message["type"] == "history_cleared":
                self.output_text.config(state=tk.NORMAL)
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, "Message history cleared\n")
                self.output_text.config(state=tk.DISABLED)
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
    
    def on_send_clicked(self):
        """Handle send button click."""
        message = self.input_text.get(1.0, tk.END).strip()
        if message and self.is_connected:
            # Schedule the async task in the event loop
            asyncio.run_coroutine_threadsafe(self.client.send_message(message), self.loop)
            self.input_text.delete(1.0, tk.END)
    
    def _update_audio_status(self, status):
        """Update audio status label."""
        try:
            self.audio_status_var.set(status)
            # Force UI update
            self.root.update_idletasks()
        except Exception as e:
            logger.error(f"Error updating audio status: {str(e)}")
    
    def _update_progress(self, value):
        """Update progress bar."""
        try:
            self.progress_bar['value'] = value
            # Force UI update
            self.root.update_idletasks()
        except Exception as e:
            logger.error(f"Error updating progress bar: {str(e)}")
    
    def _on_transcription_finished(self, text):
        """Handle completed transcription."""
        try:
            if text:
                self.input_text.delete(1.0, tk.END)
                self.input_text.insert(tk.END, text)
            self.record_button.config(text="Record Audio")
        except Exception as e:
            logger.error(f"Error handling transcription result: {str(e)}")
            self.audio_status_var.set(f"Error: {str(e)}")
            self.record_button.config(text="Record Audio")
    
    def on_clear_clicked(self):
        """Handle clear history button click."""
        if self.is_connected:
            asyncio.run_coroutine_threadsafe(self.client.clear_history(), self.loop)
    
    def on_closing(self):
        """Handle window close event."""
        if self.is_connected:
            # Schedule the close task
            asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)
            
            # Give it a moment to complete
            self.root.after(500, self.root.destroy)
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = MCPClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main() 