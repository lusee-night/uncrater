import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ClientsideFunction
import argparse
import socket
import sys
sys.path.append('..')
sys.path.append('.')
import uncrater


parser = argparse.ArgumentParser()
parser.add_argument('-i', '--interactive', action='store_true', help='Enable interactive mode')
parser.add_argument('--root', type=str, help='Root directory')

args = parser.parse_args()

interactive_mode = args.interactive
root_directory = args.root

if root_directory is None:
    root_directory = 'session'


app = dash.Dash(__name__)
global config, collection
config = {'cmd_clicks':0, 'cmd_subs':0, 'cdi_clicks':0, 'cdi_subs':0, 'cmdcmd_subs':0,
          'root':root_directory, 'uart':root_directory + '/uart.log', 'commander':root_directory + '/commander.log',
          'cdi_display': 0}
collection = uncrater.Collection(root_directory + '/cdi_output')

ta_style = {'width': '80%', 'height': '700px', 'background': 'black','color': 'white', 'font-size': '16px', 'font-family': 'monospace', 'overflow-y': 'scroll', 'overflow-x': 'scroll', 'white-space': 'pre-wrap'}
app.layout = html.Div([
    html.H1("LuSEE-Night Spectrometer Dashboard"),
    html.Table([
        html.Tr([html.Td("UART"),html.Td("COMMANDER"),html.Td("CDI")]),
        html.Tr([
        html.Td(dcc.Textarea(id='uart', value="", style=ta_style)),
        html.Td(dcc.Textarea(id='commander', value="", style=ta_style)),
        html.Td(dcc.Textarea(id='cdi', value="", style=ta_style))
        ])
    ], style={'width': '100%', 'align': 'center','margin-left': 'auto', 'margin-right': 'auto', 'text-align': 'center'}),
    html.H1("Commanding CDI"),
    html.P("CDI Command:"),
    dcc.Input(id='cdi_cmd', type='text',n_submit=0, value='10', style={'width': '5%'}),
    dcc.Input(id='cdi_arg', type='text',n_submit=0, value='0000', style={'width': '10%'}),
    html.Button('Send command', id='cmd_submit_b', n_clicks=0),  
    html.P("Commander Command:"),
    dcc.Input(id='cmd_cmd', type='text',n_submit=0, value='', style={'width': '50%'}),
    html.H1("Inspect CDI"),
    dcc.Input(id='cdi_inspect_t', type='text',n_submit=0, value='0', style={'width': '10%'}),
    html.Button('Inspect CDI packet', id='cdi_inspect_b', n_clicks=0),  

    html.Table([
        html.Tr([html.Td("Raw Packet Contents"),html.Td("Packet Contents")]),
        html.Tr([
        html.Td(dcc.Textarea(id='cdi_raw', value="", style=ta_style)),
        html.Td(dcc.Textarea(id='cdi_info', value="", style=ta_style)),
        ])
    ], style={'width': '100%', 'align': 'center','margin-left': 'auto', 'margin-right': 'auto', 'text-align': 'center'}),
    dcc.Interval(
            id='interval-component',
            interval=1*1000, # in milliseconds
            n_intervals=0
        )
])


def commander_send(msg):
    s = socket.socket()
    try:
        s.connect(('127.0.0.1', 8051))
    except ConnectionRefusedError:
        print (f"Cannot send command: {msg}")
        print (f"Is commander running? Dropping bits.")
        return
    s.send(msg.encode())
    s.close()  


app.clientside_callback(
    ClientsideFunction(
        namespace='clientside',
        function_name='scroll_to_bottom'
    ),
    Output('uart', 'n_clicks'),
    Output('commander', 'n_clicks'),
    Output('cdi', 'n_clicks'),
    Input('uart', 'value'),
    Input('commander', 'value'),
    Input('cdi', 'value'),
)


@app.callback(
    Output('uart', 'value'),
    Output('commander', 'value'),
    Output('cdi', 'value'),
    Output('cdi_raw', 'value'),
    Output('cdi_info', 'value'),
    Output('cmd_cmd', 'value'),
    Input('cmd_submit_b', 'n_clicks'),
    Input('cdi_arg', 'n_submit'),
    Input('cdi_inspect_b', 'n_clicks'),
    Input('cdi_inspect_t', 'n_submit'),
    Input('cmd_cmd', 'n_submit'),
    Input('interval-component', 'n_intervals'),
    State('cdi_cmd', 'value'),
    State('cdi_arg', 'value'),
    State('cmd_cmd', 'value'),
    State('cdi_inspect_t', 'value'),
    prevent_initial_call=True
)
def update_output(cmd_clicks, cmd_subs, cdi_clicks, cdi_subs, cmdcmd_subs, n_intervals, cdi_cmd, cdi_arg, cmdcmd, cdi_inspect_t):
    global config, collection
    collection.refresh()

    try:
        uart_value = open(config['uart']).read()
    except:
        uart_value = ""
    try:
        commander_value = open(config['commander']).read()
    except:
        commander_value = ""
    cdi_value = collection.list() 
    
    if cmd_clicks>config['cmd_clicks'] or cmd_subs>config['cmd_subs']:
        commander_send (f"# # CDI {cdi_cmd} {cdi_arg}")
        config['cmd_clicks'] = cmd_clicks
        config['cmd_subs'] = cmd_subs

    if cmdcmd_subs>config['cmdcmd_subs']:
        commander_send (cmdcmd)
        cmdcmd=""
        config['cmdcmd_subs'] = cmdcmd_subs


    if cdi_clicks>config['cdi_clicks'] or cdi_subs>config['cdi_subs']:
        config['cdi_clicks'] = cdi_clicks
        config['cdi_subs'] = cdi_subs

        try:
            config['cdi_display'] = int(cdi_inspect_t)
        except:
            config['cdi_display'] = -1
        print ('here',config['cdi_display'])

    p = config['cdi_display']
    if p>=0 and p<len(collection):
        cdi_raw_value = collection.xxd(p, intro=True)
        cdi_info_value = collection.info(p, intro=True)
    else:
        cdi_raw_value = ""
        cdi_info_value = ""
    
    return (uart_value, commander_value, cdi_value, cdi_raw_value, cdi_info_value, cmdcmd)
    
    

def update_console_1(n, console1_value):
    print ('mere')
    return console1_value + f'Update {n}\n'


if __name__ == '__main__':
    
    root = "session/"
    config['uart'] = root + '/uart.log'
    config['commander'] = root + '/commander.log'
    app.run_server(host='127.0.0.1', port='8050',debug=False)
