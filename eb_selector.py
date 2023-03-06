#!/usr/bin/env python

from astropy import log
import io
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import PIL.Image
import pickle 
import PySimpleGUI as sg
import random
import time
from tqdm import tqdm

from asassnell import varlog_parser
import asassnutils

#Dom Rowan 2021

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


def main(lc_folder, buttons=['yes', 'no']):

    left_col = [
            [sg.Text('logfile'), sg.In(size=(25, 1), enable_events=True, key='-logfile-'),
             sg.FileBrowse()],
            [sg.Button('New Logfile', button_color=('white', 'black'),
                       key='-newlogfile-'),
             sg.In(key='-newlogfile_path-', size=(12, 1))],
            [sg.Text('Catalog'), sg.In(size=(25, 1), enable_events=True,
                                       key='-catalogfile-'),
             sg.FileBrowse(file_types=(("CSV Files", "*.csv"),
                                       ("Pickles", "*.pickle")))],
            [ sg.Button(b, button_color=('white', 'black'),
                        key=f'{b}_key') for b in buttons ],
            [ sg.Text('Comment'), sg.In(key='-comment-', size=(12, 1))],
            [ sg.Text('Resize to'), sg.In(key='-W-', size=(5, 1)), sg.In(key='-H-', size=(5, 1))]]

    image_col = [[sg.Text('Currently Classifying:')],
                 [sg.Text(size=(80, 1), key='-TOUT-')],
                 [sg.Image(key='-IMAGE-', size=(300, 300))]]

    layout=[[sg.Column(left_col, element_justification='c'),
             sg.VSeperator(),
             sg.Column(image_col, element_justification='c')]]

    window=sg.Window('Eclipsing Binary Inspector', layout, resizable=True, finalize=True)

    if len(buttons) < 9:
        for i in range(len(buttons)):
            window.bind(str(i+1), f'{buttons[i]}_key')
        

    if not asassnutils.check_iter(lc_folder):
        lc_files = [ os.path.join(lc_folder, x)
                     for x in os.listdir(lc_folder)
                     if x.endswith('.jpg') ]
    else:
        lc_files = lc_folder

    df_log = None
    lightcurves_to_classify=None
    classification=None
    catalog = None
    previous = None
    logfile_path = None

    user='DMR'

    rows_to_append = []

    while True:
        event, values=window.read()

        print(event)
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        if event == sg.WIN_CLOSED or event=='Exit':
            break

        if event=='-catalogfile-':
            catalog = pd.read_csv(values['-catalogfile-'])
            continue
        elif event == '-logfile-':
            logfile_path = values['-logfile-']
            df_log = varlog_parser.parse(values['-logfile-'])
            df_log['id'] = df_log.id.astype('str')

            if catalog is not None:
                lightcurves_to_classify = [
                        os.path.join(lc_folder, catalog.lc_path.iloc[i])
                        for i in range(len(catalog))
                        if (os.path.splitext(catalog.lc_path.iloc[i])[0]
                            not in list(df_log.id)) ]
            else:
                lightcurves_to_classify = [
                        l for l in lc_files
                        if (os.path.splitext(os.path.split(l)[-1])[0]
                            not in list(df_log.id)) ]
            print(len(lightcurves_to_classify))
            random.shuffle(lightcurves_to_classify)

        elif event == '-newlogfile-':
            logfile_path = values['-newlogfile_path-']
            if os.path.isfile(logfile_path):
                log.error('logfile already exists, exiting')
                break
            df_log = pd.DataFrame(columns=['id', 'user', 'class', 'comment'])
            if catalog is not None:
                lightcurves_to_classify = [
                    os.path.join(lc_folder, catalog.lc_path.iloc[i])
                    for i in range(len(catalog)) ]
            else:
                lightcurves_to_classify = lc_files
            random.shuffle(lightcurves_to_classify)

        elif event in [ f'{b}_key' for b in buttons ] and logfile_path is not None:
            classification = event.split('_key')[0]
            window['-newlogfile_path-'].update(logfile_path)
        else:
            pass


        if lightcurves_to_classify is not None:
            if classification is not None:
                rows_to_append.append([
                        os.path.splitext(os.path.split(image)[-1])[0],
                        user, classification,
                        values['-comment-']])

                window['-comment-'].update("")

            if len(lightcurves_to_classify) != 0:
                try:

                    """
                    doc = fitz.open(lightcurves_to_classify[0])
                    image_name = os.path.split(lightcurves_to_classify[0])[-1]
                    window['-TOUT-'].update(os.path.split(lightcurves_to_classify[0])[-1])

                    #dlist = doc[0].getDisplyList()
                    dlist = doc
                    data = doc.getPagePixmap(pno=0).getPNGData()

                    image_elem = sg.Image(data=data)
                    if values['-W-'] and values['-H-']:
                        new_size=int(values['-W-']), int(values['-H-'])
                    else:
                        new_size=(1000, 1800)
                    window['-IMAGE-'].update(data=data)
                    lightcurves_to_classify = lightcurves_to_classify[1:]
                    """

                    image = lightcurves_to_classify[0]
                    window['-TOUT-'].update(
                            f'previous:{previous} current: {os.path.split(image)[-1]}')
                    if values['-W-'] and values['-H-']:
                        new_size=int(values['-W-']), int(values['-H-'])
                    else:
                        new_size=(1000, 1800)
                    #window['-IMAGE-'].update(data=convert_to_bytes(image, resize=new_size))
                    #window['-IMAGE-'].update(data=convert_to_bytes(image, resize=window['-IMAGE-'].get_size()))
                    window['-IMAGE-'].update(data=convert_to_bytes(image, resize=window.size))
                    previous = os.path.split(image)[-1]
                    lightcurves_to_classify = lightcurves_to_classify[1:]


                except Exception as E:
                    print(f' ** Error {E} **')
                    pass
            else:
                pass

    window.close()

    df_new = pd.DataFrame({'id':[ r[0] for r in rows_to_append],
                           'user': [np.array([r[1]]) for r in rows_to_append ],
                           'class': [ np.array([r[2]]) for r in rows_to_append ],
                           'comment': [ np.array([r[3]]) for r in rows_to_append]})
    if df_log is None:
        df_log = df_new
    else:
        df_log = pd.concat([df_log, df_new])

    varlog_parser.write_logfile(df_log, logfile_path)

def checkbox_scanner(lc_folder, boxes=['val1', 'val2']):

    assert(len(boxes))

    left_col = [
            [sg.Text('logfile'), sg.In(size=(25, 1), enable_events=True, key='-logfile-'),
             sg.FileBrowse()],
            [sg.Button('New Logfile', button_color=('white', 'black'),
                       key='-newlogfile-'),
             sg.In(key='-newlogfile_path-', size=(12, 1))],
            [sg.Text('Catalog'), sg.In(size=(25, 1), enable_events=True,
                                       key='-catalogfile-'),
             sg.FileBrowse(file_types=(("CSV Files", "*.csv"),
                                       ("Pickles", "*.pickle")))],
            [ sg.Button('Success', button_color=('white', 'black'),
                        key='b_success') ]]
    left_col.extend([ [ sg.Checkbox(c, default=False, key=f'cb_{c}') ]
                     for c in boxes ])
    left_col.extend([
            [sg.Button('Failure', button_color=('white', 'black'),
                     key='b_failure')],
            [ sg.Text('Comment'), sg.In(key='-comment-', size=(12, 1))],
            [ sg.Text('Resize to'), sg.In(key='-W-', size=(5, 1)), sg.In(key='-H-', size=(5, 1))]])

    image_col = [[sg.Text('Currently Classifying:')],
                 [sg.Text(size=(80, 1), key='-TOUT-')],
                 [sg.Image(key='-IMAGE-')]]

    layout=[[sg.Column(left_col, element_justification='c'),
             sg.VSeperator(),
             sg.Column(image_col, element_justification='c')]]

    window=sg.Window('Eclipsing Binary Inspector', layout, resizable=True)

    lc_files = [ os.path.join(lc_folder, x)
                 for x in os.listdir(lc_folder)
                 if x.endswith('.jpeg') ]

    result = None

    df_log = None
    lightcurves_to_classify=None
    catalog = None
    previous = None

    user='DMR'

    rows_to_append = []

    while True:
        event, values=window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        if event == sg.WIN_CLOSED or event=='Exit':
            break

        if event=='-catalogfile-':
            catalog = pd.read_csv(values['-catalogfile-'])
            continue
        elif event == '-logfile-':
            logfile_path = values['-logfile-']
            df_log = varlog_parser.parse(values['-logfile-'])
            df_log['id'] = df_log.id.astype('str')

            if catalog is not None:
                lightcurves_to_classify = [
                        os.path.join(lc_folder, catalog.lc_path.iloc[i])
                        for i in range(len(catalog))
                        if (os.path.splitext(catalog.lc_path.iloc[i])[0]
                            not in list(df_log.id)) ]
            else:
                lightcurves_to_classify = [
                        l for l in lc_files
                        if (os.path.splitext(os.path.split(l)[-1])[0]
                            not in list(df_log.id)) ]
            print(len(lightcurves_to_classify))
            random.shuffle(lightcurves_to_classify)

        elif event == '-newlogfile-':
            logfile_path = values['-newlogfile_path-']
            if os.path.isfile(logfile_path):
                log.error('logfile already exists, exiting')
                break
            df_log = pd.DataFrame(columns=['id', 'user', 'class', 'comment'])
            if catalog is not None:
                lightcurves_to_classify = [
                    os.path.join(lc_folder, catalog.lc_path.iloc[i])
                    for i in range(len(catalog)) ]
            else:
                lightcurves_to_classify = lc_files
            random.shuffle(lightcurves_to_classify)

        elif event in ['b_success', 'b_failure']:
            result = event.replace('b_', '')[0]
        else:
            pass

        if lightcurves_to_classify is not None:

            if result is not None:

                box_states = []
                for c in boxes:
                    box_states.append(values[f'cb_{c}'])

                rows_to_append.append([
                        os.path.splitext(os.path.split(image)[-1])[0],
                        user, result]+
                        box_states+[values['-comment-']])


                window['-comment-'].update("")
                for c in boxes:
                    window[f'cb_{c}'].Update(value=False)

            if len(lightcurves_to_classify) != 0:
                try:

                    image = lightcurves_to_classify[0]
                    window['-TOUT-'].update(
                            f'previous:{previous} current: {os.path.split(image)[-1]}')
                    if values['-W-'] and values['-H-']:
                        new_size=int(values['-W-']), int(values['-H-'])
                    else:
                        new_size=(1000, 1800)
                    window['-IMAGE-'].update(data=convert_to_bytes(image, resize=new_size))
                    previous = os.path.split(image)[-1]
                    lightcurves_to_classify = lightcurves_to_classify[1:]

                except Exception as E:
                    print(f' ** Error {E} **')
                    pass
            else:
                pass

    df_out = pd.DataFrame(
            rows_to_append, columns=['id', 'user', 'result']+boxes+['comment'])
    df_out.to_csv('temp.csv', index=False)

def Collapsible(layout, key, title='', arrows=(sg.SYMBOL_DOWN, sg.SYMBOL_UP), collapsed=False):
    """
    User Defined Element
    A "collapsable section" element. Like a container element that can be collapsed and brought back
    :param layout:Tuple[List[sg.Element]]: The layout for the section
    :param key:Any: Key used to make this section visible / invisible
    :param title:str: Title to show next to arrow
    :param arrows:Tuple[str, str]: The strings to use to show the section is (Open, Closed).
    :param collapsed:bool: If True, then the section begins in a collapsed state
    :return:sg.Column: Column including the arrows, title and the layout that is pinned
    """
    return sg.Column(
            [[sg.T((arrows[1] if collapsed else arrows[0]), enable_events=True, k=key+'-BUTTON-'),
                    sg.T(title, enable_events=True, key=key+'-TITLE-')],
             [sg.pin(sg.Column(layout, key=key, visible=not collapsed, metadata=arrows))]], 
            pad=(0,0))

def checkbox_with_tess_scanner(lc_folder, tess_folder, boxes=['val1', 'val2']):

    assert(len(boxes))

    left_col = [
            [sg.Text('logfile'), sg.In(size=(25, 1), enable_events=True, key='-logfile-'),
             sg.FileBrowse()],
            [sg.Button('New Logfile', button_color=('white', 'black'),
                       key='-newlogfile-'),
             sg.In(key='-newlogfile_path-', size=(12, 1))],
            [sg.Text('Catalog'), sg.In(size=(25, 1), enable_events=True,
                                       key='-catalogfile-'),
             sg.FileBrowse(file_types=(("CSV Files", "*.csv"),
                                       ("Pickles", "*.pickle")))],
            #[ sg.Checkbox('StarHorse+TESS', default=False, key=f'cb_sh_t', enable_events=True)],
            [  sg.Button('Swap to TESS', key='cb_sh_t', button_color=('white', 'black'))],
            [  sg.Button('Success', button_color=('white', 'black'),
                        key='b_success') ]]
    left_col.extend([ [ sg.Checkbox(c, default=False, key=f'cb_{c}') ]
                     for c in boxes ])
    left_col.extend([
            [sg.Button('Failure', button_color=('white', 'black'),
                     key='b_failure')],
            [ sg.Text('Comment'), sg.In(key='-comment-', size=(12, 1))],
            [ sg.Text('Resize to'), sg.In(key='-W-', size=(5, 1)), sg.In(key='-H-', size=(5, 1))]])

    section1 = [[sg.Image(key='-IMAGE-')]]
    section2 = [[sg.Image(key='-TESS-')]]

    image_col = [[sg.Text('Currently Classifying:')],
                 [sg.Text(size=(80, 1), key='-TOUT-')],
                 #[sg.Button('Swap to TESS', key='cb_sh_t', button_color=('white', 'black'))],
                 [Collapsible(section1, '-SECTION1-', collapsed=False)],
                 [Collapsible(section2, '-SECTION2-', collapsed=True)]]

    layout=[[sg.Column(left_col, element_justification='c'),
             sg.VSeperator(),
             sg.Column(image_col, element_justification='c')]]

    window=sg.Window('Eclipsing Binary Inspector', layout, resizable=True)

    lc_files = [ os.path.join(lc_folder, x)
                 for x in os.listdir(lc_folder)
                 if x.endswith('.jpeg') ]
    tess_files = [ os.path.join(tess_folder, x)
                   for x in os.listdir(tess_folder)
                   if x.endswith('.jpeg') ]

    result = None
    df_log = None
    lightcurves_to_classify=None
    catalog = None
    previous = None

    showing_tess=False

    user='DMR'

    rows_to_append = []

    while True:
        event, values=window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        if event == sg.WIN_CLOSED or event=='Exit':
            break

        if event=='-catalogfile-':
            catalog = pd.read_csv(values['-catalogfile-'])
            continue
        elif event == '-logfile-':
            logfile_path = values['-logfile-']
            df_log = pd.read_csv(values['-logfile-'])
            df_log['id'] = df_log.id.astype('str')

            #check columns
            columns = ['id', 'user', 'result']+boxes+['comment']
            if list(columns) != list(df_log.columns):
                raise ValueError('varlog does not match boxes')

            if catalog is not None:
                lightcurves_to_classify = [
                        os.path.join(lc_folder, catalog.lc_path.iloc[i])
                        for i in range(len(catalog))
                        if (os.path.splitext(catalog.lc_path.iloc[i])[0]
                            not in list(df_log.id)) ]
            else:

                lightcurves_to_classify = list(
                        pd.Series(lc_files).iloc[~pd.Series(lc_files).index.isin(
                                np.where(pd.Series(np.array(list(pd.Series(
                                        lc_files).str.split('/').values))[:,-1]).isin(
                                                df_log.id+'.jpeg'))[0])])
                """
                lightcurves_to_classify = [
                        l for l in tqdm(lc_files)
                        if (os.path.splitext(os.path.split(l)[-1])[0]
                            not in list(df_log.id)) ]
                """
            print(len(lightcurves_to_classify))
            random.shuffle(lightcurves_to_classify)

        elif event == '-newlogfile-':
            logfile_path = values['-newlogfile_path-']
            if os.path.isfile(logfile_path):
                log.error('logfile already exists, exiting')
                break
            if catalog is not None:
                lightcurves_to_classify = [
                    os.path.join(lc_folder, catalog.lc_path.iloc[i])
                    for i in range(len(catalog)) ]
            else:
                lightcurves_to_classify = lc_files
            random.shuffle(lightcurves_to_classify)

        elif event in ['b_success', 'b_failure']:
            result = event.replace('b_', '')[0]

        elif event == 'cb_sh_t':
            showing_tess = not showing_tess
            window['-SECTION1-'].update(visible=not window['-SECTION1-'].visible)
            window['-SECTION2-'].update(visible=not window['-SECTION2-'].visible)

            if showing_tess:
                window['cb_sh_t'].Update('Swap to ASAS-SN')
            else:
                window['cb_sh_t'].Update('Swap to TESS')

            continue

        else:
            pass

        if lightcurves_to_classify is not None:

            if result is not None:

                box_states = []
                for c in boxes:
                    box_states.append(values[f'cb_{c}'])

                rows_to_append.append([
                        os.path.splitext(os.path.split(image)[-1])[0],
                        user, result]+
                        box_states+[values['-comment-']])


                window['-comment-'].update("")
                for c in boxes:
                    window[f'cb_{c}'].Update(value=False)

            if len(lightcurves_to_classify) != 0:
                try:

                    image = lightcurves_to_classify[0]
                    tess_image = os.path.join(tess_folder, os.path.split(image)[-1])

                    window['-TOUT-'].update(
                            f'previous:{previous} current: {os.path.split(image)[-1]}')
                    if values['-W-'] and values['-H-']:
                        new_size=int(values['-W-']), int(values['-H-'])
                    else:
                        new_size=(900, 900)
                    window['-IMAGE-'].update(data=convert_to_bytes(image, resize=new_size))
                    window['-TESS-'].update(data=convert_to_bytes(tess_image, resize=(900, 900)))
                    previous = os.path.split(image)[-1]
                    lightcurves_to_classify = lightcurves_to_classify[1:]

                except Exception as E:
                    print(f' ** Error {E} **')
                    pass
            else:
                pass

    df_out = pd.concat([df_log, pd.DataFrame(
            rows_to_append, columns=['id', 'user', 'result']+boxes+['comment'])])
    df_out.to_csv(logfile_path, index=False)


if __name__ == '__main__':
    
   #main('scan') 
   #main('ea_sample_period_search_plots', buttons=['input', 'v', 'g', 'combined'])
   #main('ea_sample_period_search_plots_abls', buttons=['input', 'v', 'g', 'combined'])
   #main('sigma_clipping_plots', buttons=['y', 'n'])
   #checkbox_scanner('scan', boxes=['val1', 'val2', 'val3', 'val4'])
   #checkbox_with_tess_scanner('scanner_temp', 'scanner_temp_tess', 
   #                           boxes=['deep eclipse', 'bad period', 'bad incl'])
   #main('tess_plots_nm', buttons=['good', 'half', 'double', 'other'])

   main('extra_physics', 
        buttons=['multiple', 'pulsations', 'tilted_eclipses', 'spots',
                 'other', 'check'])
                         


