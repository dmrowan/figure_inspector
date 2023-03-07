#!/usr/bin/env python

import argparse
import io
import numpy as np
import os
import pandas as pd
import random
import PIL.Image
import pickle
import PySimpleGUI as sg

from . import utils

#Dom Rowan 2023

desc="""
Tool to inspect figures and generate logfile
"""

def convert_to_bytes(file_or_bytes, resize=None):
    '''
    Will convert into bytes and optionally resize an image that is a file or a base64 bytes object.
    Turns into  PNG format in the process so that can be displayed by tkinter
    :param file_or_bytes: either a string filename or a bytes base64 image object
    :type file_or_bytes:  (Union[str, bytes])
    :param resize:  optional new size
    :type resize: (Tuple[int, int] or None)
    :return: (bytes) a byte-string object
    :rtype: (bytes)
    '''
    if isinstance(file_or_bytes, str):
        img = PIL.Image.open(file_or_bytes)
    else:
        try:
            img = PIL.Image.open(io.BytesIO(base64.b64decode(file_or_bytes)))
        except Exception as e:
            dataBytesIO = io.BytesIO(file_or_bytes)
            img = PIL.Image.open(dataBytesIO)

    cur_width, cur_height = img.size
    if resize:
        new_width, new_height = resize
        scale = min(new_height/cur_height, new_width/cur_width)
        img = img.resize((int(cur_width*scale), int(cur_height*scale)), PIL.Image.ANTIALIAS)
    with io.BytesIO() as bio:
        img.save(bio, format="PNG")
        del img
        return bio.getvalue()


class Log:

    def __init__(self, folder):
        
        if not utils.check_iter(folder):
            files = [ os.path.join(folder, x)
                         for x in os.listdir(folder)
                         if (x.endswith('.jpg') or x.endswith('.jpeg'))]
        else:
            files = folder

        df = pd.DataFrame({'file':files})
        df['id'] = [ os.path.splitext(os.path.split(f)[-1])[0] for f in df.file ]
        df['id'] = df.id.astype(str)
        self.df = df

        self.start_index = None
        log.logfile_path = None

    def add_log(self, file):
        
        df_existing = pd.read_csv(file, header=None)
        df_existing.columns = ['id', 'user', 'class', 'comment']
        df_existing['id'] = df_existing.id.astype(str)

        self.df = self.df.merge(df_existing, how='left', on='id')
        self.df = self.df.reset_index(drop=True)
        self.df = self.df.fillna('')

        print(self.df)

        self.logfile_path = file

    def set_order(self):

        for c in ['user', 'class', 'comment']:
            if c not in self.df.columns:
                self.df[c] = ''

        idx = np.where(self.df['class'] == '')[0]

        df_rand = self.df.iloc[idx].sample(frac=1)
        df_classified = self.df.iloc[~self.df.index.isin(idx)]
       
        self.df = pd.concat([df_classified, df_rand]).reset_index(drop=True)
        
        self.start_index = len(df_classified)
        self._current_index = self.start_index

    @property
    def current_index(self):
        return self._current_index

    def move_forward(self):
        if self._current_index < len(self.df) - 1:
            self._current_index += 1

    def move_backwards(self):
        if self._current_index > self.start_index + 1:
            self._current_index -= 1
        
    def classify(self, classification, comment='', user=os.getlogin()):
        
        self.df['class'].iat[self.current_index] = classification
        self.df['comment'].iat[self.current_index] = comment
        self.df['user'].iat[self.current_index] = user

    def write_log(self):
        
        idx = np.where(self.df['class'] != '')[0]
        self.df[['id', 'user', 'class', 'comment']].iloc[idx].to_csv(self.logfile_path, header=None, index=False)


def classify(folder, buttons=['yes', 'no']):
    
    sg.theme("DarkGrey")
    left_col = [
            [sg.Text('logfile'), sg.In(size=(25, 1), enable_events=True, key='-logfile-'),
             sg.FileBrowse()],
            [sg.Button('New Logfile', 
                       key='-newlogfile-'),
             sg.In(key='-newlogfile_path-', size=(12, 1))],
            [ sg.Button(b, 
                        key=f'{b}_key') for b in buttons ],
            [ sg.Text('Comment'), sg.In(key='-comment-', size=(12, 1))],
            [ sg.Button('Go Back', key='-go-back-') ]]

    image_col = [[sg.Text('Currently Classifying:')],
                 [sg.Text(size=(80, 1), key='-TOUT-')],
                 [sg.Image(key='-IMAGE-', size=(300, 300))]]

    layout=[[sg.Column(left_col, element_justification='c'),
             sg.VSeperator(),
             sg.Column(image_col, element_justification='c')]]

    window=sg.Window('Figure Inspector', layout, resizable=True, finalize=True ,location=(0,0))

    if len(buttons) < 9:
        for i in range(len(buttons)):
            window.bind(str(i+1), f'{buttons[i]}_key')

    window.bind('<Configure>',"window_resize_event")

    log = Log(folder)
    user = os.getlogin()


    df_log = None
    files_to_classify = None
    classification = None
    previous = None
    logfile_path = None
    need_to_resize=False

    current_size = window.size
    resize=None

    user = os.getlogin()

    rows_to_append = []
    while True:
        
        event, values = window.read()

        #Exit the loop if window is closed
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        elif event == sg.WIN_CLOSED or event=='Exit':
            break
        elif event == "window_resize_event":
            continue
        elif event == '-logfile-':
            logfile_path = values['-logfile-']
            log.add_log(logfile_path)
            log.set_order()
        
        elif event == '-newlogfile-':
            logfile_path = values['-newlogfile_path-']
            if os.path.isfile(logfile_path):
                continue
            log.logfile_path = logfile_path
            log.set_order()

        elif event == '-go-back-':
            log.move_backwards()
            try:
                image = log.df.file.iloc[log.current_index]
                print(image)
                
                new_size = window.size
                if new_size != current_size:
                    need_to_resize = True
                else:
                    need_to_resize=False

                if log.start_index != 0:
                    previous = log.df.id.iloc[log.current_index - 1]
                else:
                    previous = None


                window['-TOUT-'].update(
                        f'previous:{previous} current: {log.df.id.iloc[log.current_index]}')
                if need_to_resize:
                    resize=window['-IMAGE-'].get_size()
                else:
                    resize=resize
                    
                window['-IMAGE-'].update(
                        data=convert_to_bytes(image, resize=resize))

                need_to_resize=False
                current_size = window.size


            except Exception as E:
                print(f' ** Error {E} **')
                pass

            continue
            
        elif event in [ f'{b}_key' for b in buttons ] and logfile_path is not None:
            classification = event.split('_key')[0]
            window['-newlogfile_path-'].update(logfile_path)
        else:
            pass


        if (log.start_index is not None):
            
            if classification is not None:

                log.classify(classification, comment=values['-comment-'], user=user)
                log.move_forward()
        
            if log.start_index != len(log.df) - 1:

                try:
                    image = log.df.file.iloc[log.current_index]
                    print(image, 'main')
                    

                    new_size = window.size
                    if new_size != current_size:
                        need_to_resize = True
                    else:
                        need_to_resize=False

                    if log.start_index != 0:
                        previous = log.df.id.iloc[log.current_index - 1]
                    else:
                        previous = None


                    window['-TOUT-'].update(
                            f'previous:{previous} current: {log.df.id.iloc[log.current_index]}')
                    if need_to_resize:
                        resize=window['-IMAGE-'].get_size()
                    else:
                        resize=resize
                        
                    window['-IMAGE-'].update(
                            data=convert_to_bytes(image, resize=resize))

                    need_to_resize=False
                    current_size = window.size


                except Exception as E:
                    print(f' ** Error {E} **')
                    pass
            else:
                pass

    window.close()

    if log.logfile_path is not None:
        log.write_log()
        pass
        

if __name__ == '__main__':
    
    classify()
