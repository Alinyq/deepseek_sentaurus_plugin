#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCAD File Reader - Read and parse TCAD files
"""

import os


class TCADFileReader:
    """Reader for TCAD files (.cmd, .plt, .log, etc.)"""
    
    def read_file(self, filepath, max_lines=1000):
        """Read file content"""
        if not os.path.exists(filepath):
            return f"Error: File not found: {filepath}"
            
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            if len(lines) > max_lines:
                content = ''.join(lines[:max_lines])
                content += f"\n... (file truncated, showing first {max_lines} lines of {len(lines)})"
            else:
                content = ''.join(lines)
                
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def read_cmd_file(self, filepath):
        """Read TCAD command file (.cmd)"""
        return self.read_file(filepath)
    
    def read_plt_file(self, filepath):
        """Read plot data file (.plt) - extract key info"""
        content = self.read_file(filepath, max_lines=200)
        return content
    
    def read_log_file(self, filepath):
        """Read log file (.log) - extract key info"""
        content = self.read_file(filepath, max_lines=500)
        return content
