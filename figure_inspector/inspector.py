#!/usr/bin/env python

from astropy import log
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

    if not utils.check_iter(folder):
        files = [ os.path.join(folder, x)
                     for x in os.listdir(folder)
                     if (x.endswith('.jpg') or x.endswith('.jpeg'))]
    else:
        files = folder

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
        elif event == '-logfile-':
            logfile_path = values['-logfile-']
            df_log = pd.read_csv(logfile_path, header=None)
        
            files_to_classify = [
                    f for f in files_to_classify
                    if (os.path.splitext(os.path.split(f)[-1])[0]
                        not in list(df_log[df_log.columns[0]]).astype(str)) ]

            random.shuffle(files_to_classify)

        elif event == '-newlogfile-':
            logfile_path = values['-newlogfile_path-']
            if os.path.isfile(logfile_path):
                log.error('logfile already_exists')
                continue
            df_log = pd.DataFrame(columns=['id', 'user', 'class', 'comment'])
            
            files_to_classify = files
            random.shuffle(files_to_classify)

        elif event in [ f'{b}_key' for b in buttons ] and logfile_path is not None:
            classification = event.split('_key')[0]
            window['-newlogfile_path-'].update(logfile_path)

        else:
            pass

        if event == "window_resize_event":
            continue

        if event == '-go-back-':
            last_entry = rows_to_append.pop(-1)
            last_fname = last_entry[0] 
            print(last_fname)
            files_to_classify.insert(0, last_fname)
            print('------')
            print(files_to_classify[:5])
            print('------')
            continue



        if files_to_classify is not None:
            
            if classification is not None:
                
                new_row = [image,
                           os.path.splitext(os.path.split(image)[-1])[0],
                           user,
                           classification,
                           values['-comment-']]

                rows_to_append.append(new_row)

            if len(files_to_classify):

                print(files_to_classify[:4])
                
                try:
                    new_size = window.size
                    if new_size != current_size:
                        need_to_resize = True
                    else:
                        need_to_resize=False
                    image = files_to_classify[0] 

                    if len(rows_to_append):
                        previous = rows_to_append[-1][0]
                    else:
                        previous = None


                    window['-TOUT-'].update(
                            f'previous:{previous} current: {os.path.splitext(os.path.split(image)[-1])[0]}')
                    if need_to_resize:
                        resize=window['-IMAGE-'].get_size()
                    else:
                        resize=resize
                        
                    window['-IMAGE-'].update(
                            data=convert_to_bytes(image, resize=resize))

                    need_to_resize=False
                    current_size = window.size

                    #previous = os.path.splitext(os.path.split(image)[-1])[0]
                    files_to_classify = files_to_classify[1:]
                except Exception as E:
                    print(f' ** Error {E} **')
                    pass
            else:
                pass

    window.close()

    df_new = pd.DataFrame({'id':[r[0] for r in rows_to_append],
                           'user':[r[1] for r in rows_to_append],
                           'class':[r[2] for r in rows_to_append],
                           'comment':[r[3] for r in rows_to_append]})

    if df_log is None:
        df_log = df_new
    else:
        df_log = pd.concat([df_log, df_new])

    #df_log.to_csv(logfile_path, header=None)

        

if __name__ == '__main__':
    
    classify()
