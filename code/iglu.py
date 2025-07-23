from gridworld.data.adapter.parse import ActionsParser 
from gridworld.data.cdm_dataset import DATA_PREFIX
from iglu_dataset_scripts import MultiturnDataset
import pathlib
import functools
import pandas as pd

def remove_duplicates(xs):
    result = {}
    for coord, color in xs: 
        result[coord] = (coord, color)
    return list(result.values())

def grid_same_as_last(events, new_event):
    if events:
        if set(events[-1].grid) != set(new_event.grid):
           events.append(new_event) 
    else:
        if new_event.params != ('start_recover_world_state',):
            events.append(new_event)
    return events


colours = ["air", "blue", "green", "red", "orange", "purple", "yellow"]

def get_tasknames():
    path = pathlib.Path(DATA_PREFIX)
    parser = ActionsParser(hits_table=f"{path}/dialogs.csv", single_turn=False)
    builder_data_path = path / 'builder-data'
    data_dirs = list(builder_data_path.glob('*-c*/'))
    return [data_dir.name for data_dir in data_dirs]
#
#def get_data():
#    path = pathlib.Path(DATA_PREFIX)
#    parser = ActionsParser(hits_table=f"{path}/dialogs.csv", single_turn=False)
#    builder_data_path = path / 'builder-data'
#    data_dirs = list(builder_data_path.glob('*-c*/'))
#    results = {}
#    for data_dir in data_dirs:
#        session_id = data_dir.name
#        try:
#            session = parser.parse_session(data_dir.parent, session=session_id) 
#            results[session_id] = []
#            last_coloured_grid = set()
#            coloured_grid = None
#            for i, dialog in enumerate(session.dialogs):
#                step = {}
#                step["dialog"] = dialog
#                step["actions"] = []
#                events = session.events.get(i+2)
#                if events:
#                    #position = events[0].position
#                    #camera = events[0].camera
#                    block_events = functools.reduce(grid_same_as_last, events, []) 
#                    for e in block_events:
#                        coloured_grid = remove_duplicates([((x,y+1,z),colours[color_id]) for x,y,z,color_id in e.grid])
#                        added = set(coloured_grid)-last_coloured_grid
#                        removed = last_coloured_grid-set(coloured_grid)
#                        step["actions"].append({"grid":coloured_grid, "added":added, "removed":removed, "position": e.position, "camera": e.camera})
#                        #step["actions"].append({"grid":coloured_grid, "added":added, "removed":removed, "position": position, "camera": camera})
#                        #print(f"\tgrid: {coloured_grid}")
#                        last_coloured_grid=set(coloured_grid)
#                results[session_id].append(step)
#        except Exception:
#            print(f"Unable to process {session_id}") 
#            
#        #print(data_dir.name)
#    return results

def get_data(task):
    path = pathlib.Path(DATA_PREFIX)
    parser = ActionsParser(hits_table=f"{path}/dialogs.csv", single_turn=False)
    df = pd.read_csv(f"{path}/dialogs.csv")
    dialogs_df = df[df['PartitionKey']==task]
    builder_data_path = path / 'builder-data'
    #data_dirs = list(builder_data_path.glob('*-c*/'))
    result = []
    session_id = task#data_dir.name
    data_dir = builder_data_path / session_id
    #try:
    session = parser.parse_session(data_dir.parent, session=session_id) 
    result = []
    last_coloured_grid = set()
    coloured_grid = None
    for i, dialog in enumerate(session.dialogs):
        #print("* input instruction\n", dialogs_df[dialogs_df['StepId']==i+2][['PartitionKey','StepId','InputInstruction','IsInstructionClear']])
        #print("* input instruction clear\n", dialogs_df[dialogs_df['StepId']==i+2][['IsInstructionClear']])
        step = {}
        if dialog == "A: nan":
            continue
        #print("* input dialog", dialog)
        dialog = (dialog or "").replace("A: ", "<Architect> ").replace("B: ", "<Builder> ")
        step["dialog"] = dialog
        step["actions"] = []
        events = session.events.get(i+2)
        if events:
            #position = events[0].position
            #camera = events[0].camera
            #for event in events:
            #    print(event.grid)
            block_events = functools.reduce(grid_same_as_last, events, []) 
            for e in block_events:
                coloured_grid = remove_duplicates([((x,y+1,z),colours[color_id]) for x,y,z,color_id in e.grid])
                print(coloured_grid)
                print(f"position: {e.position}; camera: {e.camera}")
                added = set(coloured_grid)-last_coloured_grid
                removed = last_coloured_grid-set(coloured_grid)
                #print(coloured_grid)
                step["actions"].append({"grid":coloured_grid, "added":added, "removed":removed, "position": e.position, "camera": e.camera})
                #step["actions"].append({"grid":coloured_grid, "added":added, "removed":removed, "position": position, "camera": camera})
                #print(f"\tgrid: {coloured_grid}")
                last_coloured_grid=set(coloured_grid)
        print("======")
        if step['dialog'] or step['actions']:
            result.append(step)
    #except Exception:
    #    print(f"Unable to process {session_id}") 
            
        #print(data_dir.name)
    return result


if __name__ == "__main__":
    result = get_data("1-c118")
    for x in result:
        print(x)
    #for k, data in get_data().items():
    #    print(k)
    #    print(data)
    #    break
