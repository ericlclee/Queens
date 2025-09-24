from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import matplotlib.animation as animation
import datetime
import os
import time
import pytz
from pathlib import Path

class Cell:
    def __init__(self, id, color, row, column, status):
        self.id = id
        self.color = color
        self.row = row
        self.column = column
        self.status = status

    def __eq__(self, other):
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
    
class Board: 
    def __init__(self, state):
        self.cells = [cell for state_list in state.values() for cell in state_list]
        self.available = state['available']
        self.selected = state['selected']
        self.eliminated = state['eliminated']
        self.cell_by_row = defaultdict(set)
        self.cell_by_column = defaultdict(set)
        self.cell_by_rowcol = {}
        self.cell_by_color = defaultdict(set)
        self.colors = set()
        self.board_size = int(len(self.cells) ** 0.5)
        for cell in self.cells:
            self.colors.add(cell.color)
            self.cell_by_row[cell.row].add(cell)
            self.cell_by_column[cell.column].add(cell)
            self.cell_by_rowcol[(cell.row, cell.column)] = cell
            self.cell_by_color[cell.color].add(cell)
    
    def evaluate_partitions(self):
        edge_dict = dict()
        for cell in self.available:
            color = cell.color
            if cell.color not in edge_dict.keys():
                edge_dict[color] = {
                    'north_edge': cell.row,
                    'south_edge': cell.row,
                    'west_edge': cell.column,
                    'east_edge': cell.column
                }
            else:
                edge_dict[color]['north_edge'] = min(edge_dict[color]['north_edge'], cell.row)
                edge_dict[color]['south_edge'] = max(edge_dict[color]['south_edge'], cell.row)
                edge_dict[color]['west_edge'] = min(edge_dict[color]['west_edge'], cell.column)
                edge_dict[color]['east_edge'] = max(edge_dict[color]['east_edge'], cell.column)
        
        north_edges = set([edge_dict[color]['north_edge'] for color in edge_dict])
        south_edges = set([edge_dict[color]['south_edge'] for color in edge_dict])
        west_edges = set([edge_dict[color]['west_edge'] for color in edge_dict])
        east_edges = set([edge_dict[color]['east_edge'] for color in edge_dict])

        cleaned_partitions = []
        for north_edge in north_edges:
            for south_edge in south_edges:
                if south_edge < north_edge:
                    continue
                included_cells = set()
                inlcuded_colors = set()
                excluded_colors = set()
                for cell in self.available:
                    if cell.row >= north_edge and cell.row <= south_edge:
                        included_cells.add(cell)
                        inlcuded_colors.add(cell.color)
                    else:
                        excluded_colors.add(cell.color)
                only_included = inlcuded_colors.difference(excluded_colors)
                if len(only_included) > (south_edge - north_edge + 1):
                    cleaned_partitions.append({'north_edge': north_edge, 'south_edge': south_edge, 'west_edge': 1, 'east_edge': self.board_size, 'cleaned_cells': []})
                    return cleaned_partitions, True
                elif len(only_included) == (south_edge - north_edge + 1):
                    cleaned_cells = []
                    for cell in included_cells:
                        if cell.color in excluded_colors:
                            cleaned_cells.append(cell)
                            self.eliminated.add(cell)
                            self.available.remove(cell)
                    if len(cleaned_cells) > 0:
                        cleaned_partitions.append({'north_edge': north_edge, 'south_edge': south_edge, 'west_edge': 1, 'east_edge': self.board_size, 'cleaned_cells': cleaned_cells})
        
        for west_edge in west_edges:
            for east_edge in east_edges:
                if east_edge < west_edge:
                    continue
                included_cells = set()
                inlcuded_colors = set()
                excluded_colors = set()
                for cell in self.available:
                    if cell.column >= west_edge and cell.column <= east_edge:
                        included_cells.add(cell)
                        inlcuded_colors.add(cell.color)
                    else:
                        excluded_colors.add(cell.color)
                only_included = inlcuded_colors.difference(excluded_colors)
                if len(only_included) > (east_edge - west_edge + 1):
                    cleaned_partitions.append({'north_edge': 1, 'south_edge': self.board_size, 'west_edge': west_edge, 'east_edge': east_edge, 'cleaned_cells': []})
                    return cleaned_partitions, True
                elif len(only_included) == (east_edge - west_edge + 1):
                    cleaned_cells = []
                    for cell in included_cells:
                        if cell.color in excluded_colors:
                            cleaned_cells.append(cell)
                            self.eliminated.add(cell)
                            self.available.remove(cell)
                    if len(cleaned_cells) > 0:
                        cleaned_partitions.append({'north_edge': 1, 'south_edge': self.board_size, 'west_edge': west_edge, 'east_edge': east_edge, 'cleaned_cells': cleaned_cells})

        return cleaned_partitions, False
                    
                                    
    def color_counts(self):
        color_counts = defaultdict(int)
        for cell in self.available:
            color_counts[cell.color] += 1

        return color_counts
    
    def calculate_constraint_heuristic(self, selected_cell):
        sel_row = selected_cell.row
        sel_col = selected_cell.column
        constraint_cells = self.cell_by_row[sel_row].union(self.cell_by_column[sel_col])
        cell = self.cell_by_rowcol.get((selected_cell.row + 1, selected_cell.column + 1))
        if cell is not None: 
            constraint_cells.add(cell)
        cell = self.cell_by_rowcol.get((selected_cell.row - 1, selected_cell.column - 1))
        if cell is not None:
            constraint_cells.add(cell)
        cell = self.cell_by_rowcol.get((selected_cell.row + 1, selected_cell.column - 1))
        if cell is not None:
            constraint_cells.add(cell)
        cell = self.cell_by_rowcol.get((selected_cell.row - 1, selected_cell.column + 1))
        if cell is not None:
            constraint_cells.add(cell)
        constraint_cells = constraint_cells.difference(self.cell_by_color[selected_cell.color]).intersection(self.available)
        score = len(constraint_cells)
        return score
    
    def get_priority_queue(self):
        color_counts = self.color_counts()
        min_count = min(color_counts.values())
        candidate_cells = []
        for color, count in color_counts.items():
            if count == min_count:
                for cell in self.available:
                    if cell.color == color:
                        candidate_cells.append(cell)

        queue = []
        for cell in candidate_cells:
            score = self.calculate_constraint_heuristic(cell)
            queue.append((cell, score))

        queue = sorted(queue, key=lambda x: x[1], reverse=False)
        selected_color = queue[0][0].color
        queue = [(cell, score) for cell, score in queue if cell.color == selected_color]
        
        return queue
    
    def copy(self):
        board_state = {
            'available': self.available.copy(),
            'selected': self.selected.copy(),
            'eliminated': self.eliminated.copy()
        }
        new_board = Board(board_state)
        return new_board

    def forecast_state(self, selected_cell):
        new_board = self.copy()
        new_board.selected.add(selected_cell)
        new_board.available.remove(selected_cell)
        sel_row = selected_cell.row
        sel_col = selected_cell.column
        constrained_cells = self.cell_by_row[sel_row].union(self.cell_by_column[sel_col]).union(self.cell_by_color[selected_cell.color])
        cell = self.cell_by_rowcol.get((selected_cell.row + 1, selected_cell.column + 1))
        if cell is not None: 
            constrained_cells.add(cell)
        cell = self.cell_by_rowcol.get((selected_cell.row - 1, selected_cell.column - 1))
        if cell is not None:
            constrained_cells.add(cell)
        cell = self.cell_by_rowcol.get((selected_cell.row + 1, selected_cell.column - 1))
        if cell is not None:
            constrained_cells.add(cell)
        cell = self.cell_by_rowcol.get((selected_cell.row - 1, selected_cell.column + 1))
        if cell is not None:
            constrained_cells.add(cell)
        constrained_cells = constrained_cells.intersection(self.available)
        constrained_cells.remove(selected_cell)
        for cell in constrained_cells:
            new_board.eliminated.add(cell)
            new_board.available.remove(cell)
        return new_board
    
    def display(self, scale = 3, margin = 0.5):
        color_map = {
            "Lime Yellow": "#E8E15A",     
            "Pastel Green": "#A8D8B9",    
            "Lavender": "#B8A6E1",        
            "Peach Orange": "#FF9B85",    
            "Rose Pink": "#F1A1C4",       
            "Soft Blue": "#77B9D7",       
            "Muted Teal": "#4C8C8C",      
            "Vibrant Coral": "#F36C56",     
            "Light Gray": "#D3D3D3",        
            "Warm Beige": "#F2E2B1",        
            "Bright Cyan": "#4FB0B7"
        }
        fig, ax = plt.subplots()
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlim(1-margin, int((len(self.cells)) ** (1/2) + 1) * scale + margin)
        ax.set_ylim((int((len(self.cells)) ** (1/2) + 1) * scale + margin), (1-margin)) 
        ax.set_aspect('equal')
        for spine in ax.spines.values():
            spine.set_visible(False)
        for cell in self.cells:
            ax.add_patch(plt.Rectangle(
                (cell.column * scale, cell.row * scale),
                1 * scale, 
                1 * scale, 
                facecolor=color_map[cell.color], 
                edgecolor='black',
                linewidth= 3 * scale/4)
            )
        for cell in self.selected:
            ax.text((cell.column+0.5) * scale, (cell.row+0.5) * scale, '\u265B', fontsize=6 * scale, ha='center', va='center', color = 'gold')
        for cell in self.eliminated:
            ax.text((cell.column+0.5) * scale, (cell.row+0.5) * scale, '\u00D7', fontsize=2 * scale, ha='center', va='center')
        plt.show()

class Solver():
    def __init__(self, date = None):
        self.move_history = []
        self.solution_board = None
        self.date = date
        self.move_status = [
            'Solution Found!',
            'Searching...',
            'Terminal Node Found, Backtracking...',
            'Trimming Partition...',
            'Overloaded Partition, Backtracking...'
        ]
        
    def backtrack(self, board, history = False):
        e_colors = set([cell.color for cell in board.eliminated])
        s_colors = set([cell.color for cell in board.selected])
        a_colors = set([cell.color for cell in board.available])
        if len(e_colors.difference(s_colors, a_colors)) > 0:
            if history:
                self.move_history.append({
                    'selected': board.selected, 
                    'eliminated': board.eliminated, 
                    'status': 2
                    })
            return board, False
        
        if len(board.selected) == len(board.colors):
            if history:
                self.move_history.append({
                    'selected': board.selected, 
                    'eliminated': board.eliminated, 
                    'status': 0
                    })
            return board, True
        
        if history:
            self.move_history.append({
                'selected': board.selected.copy(), 
                'eliminated': board.eliminated.copy(), 
                'status': 1
                })
        
        cleaned_partitions, solution_infeasible = board.evaluate_partitions()

        if history:
            for partition in cleaned_partitions:
                self.move_history.append({
                    'selected': board.selected, 
                    'eliminated': partition['cleaned_cells'], 
                    'status': 3, 
                    'partition_data': partition
                    })

        if solution_infeasible:
            if history:
                self.move_history.append({
                    'selected': board.selected, 
                    'eliminated': board.eliminated,
                    'status': 4
                    })
            return board, False

        priority_queue = board.get_priority_queue()

        for selected_cell, _ in priority_queue:
            new_board, solution = self.backtrack(board.forecast_state(selected_cell), history=history)
            if solution:
                self.solution_board = new_board
                return new_board, True
        return new_board, False
    
    def draw_solution(self, scale = 3, margin = 0.5, interval = 50, save = False):
        color_map = {
            "Lime Yellow": "#E8E15A",     
            "Pastel Green": "#A8D8B9",    
            "Lavender": "#B8A6E1",        
            "Peach Orange": "#FF9B85",    
            "Rose Pink": "#F1A1C4",       
            "Soft Blue": "#77B9D7",       
            "Muted Teal": "#4C8C8C",      
            "Vibrant Coral": "#F36C56",     
            "Light Gray": "#D3D3D3",        
            "Warm Beige": "#F2E2B1",        
            "Bright Cyan": "#4FB0B7"        
        }
        def draw_board(ax, move_history, move_number):            
            ax.cla()
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_xlim(1 - margin, int((len(self.solution_board.cells)) ** 0.5 + 1) * scale + margin)
            ax.set_ylim((int((len(self.solution_board.cells)) ** 0.5 + 1) * scale + margin), (1 - margin)) 
            ax.set_aspect('equal')

            for spine in ax.spines.values():
                spine.set_visible(False)

            alpha = 0.3 if (move_history[move_number]['status'] == 3) else 1
            for cell in self.solution_board.cells:
                ax.add_patch(plt.Rectangle((cell.column * scale, cell.row * scale),1 * scale, 1 * scale, facecolor=color_map[cell.color], edgecolor='black',linewidth=3 * scale/4, alpha=alpha))

            for cell in move_history[move_number]['selected']:
                ax.text((cell.column + 0.5) * scale, (cell.row + 0.5) * scale, '\u265B', fontsize=5 * scale, ha='center', va='center')

            if move_history[move_number]['status'] != 3:
                for cell in move_history[move_number]['eliminated']:
                    ax.text((cell.column + 0.5) * scale, (cell.row + 0.5) * scale, '\u00D7', fontsize=2 * scale, ha='center', va='center')
            else:
                ax.add_patch(
                    plt.Rectangle(
                        (move_history[move_number]['partition_data']['west_edge'] * scale, (move_history[move_number]['partition_data']['south_edge'] + 1) * scale),
                        (move_history[move_number]['partition_data']['east_edge'] - move_history[move_number]['partition_data']['west_edge'] + 1) * scale,
                        -(move_history[move_number]['partition_data']['south_edge'] - move_history[move_number]['partition_data']['north_edge'] + 1) * scale,
                        facecolor='black', edgecolor='none', linewidth=3 * scale/4, alpha = 0.2
                    )
                )
                for cell in move_history[move_number]['eliminated']:
                    ax.text((cell.column + 0.5) * scale, (cell.row + 0.5) * scale, '\u00D7', fontsize=2 * scale, ha='center', va='center', color='black', fontweight='bold')
                    ax.add_patch(plt.Rectangle((cell.column * scale, cell.row * scale),1 * scale, 1 * scale, facecolor=color_map[cell.color], edgecolor='black',linewidth=3 * scale/4, alpha=1))
                ax.add_patch(
                    plt.Rectangle(
                        (move_history[move_number]['partition_data']['west_edge'] * scale, (move_history[move_number]['partition_data']['south_edge'] + 1) * scale),
                        (move_history[move_number]['partition_data']['east_edge'] - move_history[move_number]['partition_data']['west_edge'] + 1) * scale,
                        -(move_history[move_number]['partition_data']['south_edge'] - move_history[move_number]['partition_data']['north_edge'] + 1) * scale,
                        facecolor='none', edgecolor='black', linewidth=3 * scale/4, alpha = 0.7
                    )
                )
                previous_move_number = move_number
                while move_history[previous_move_number]['status'] == 3:
                    previous_move_number -= 1
                    for cell in move_history[previous_move_number]['eliminated']:
                        ax.text((cell.column + 0.5) * scale, (cell.row + 0.5) * scale, '\u00D7', fontsize=2 * scale, ha='center', va='center')

            ax.text(3, (int((len(self.solution_board.cells)) ** 0.5 + 1) * scale + margin), f'Move: {move_number + 1}, Status: {self.move_status[move_history[move_number]["status"]]}', fontsize=2.5*scale, ha='left', va='top')

            # if move_number > 0:
            #     if move_history[move_number - 1]['status'] in (2,4):
            #         time.sleep(0.2)

        fig, ax = plt.subplots()
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0.15, hspace=0, wspace=0)
        draw_board(ax, self.move_history, 0)

        def update(val):
            if val >= len(self.move_history):
                val = len(self.move_history) - 1
            draw_board(ax, self.move_history, val)
            fig.canvas.draw_idle()

        ani = animation.FuncAnimation(fig, update, frames = range(len(self.move_history)*2), interval=interval, repeat = False)
        pacific_tz = pytz.timezone('America/Los_Angeles')
        
        if save:
            if self.date:
                date = self.date
            else:
                date = datetime.datetime.now(pytz.utc).astimezone(pacific_tz)
                date = datetime.datetime.strftime(date, '%Y%m%d')
            file_dir = Path(__file__).parent
            output_dir = file_dir / "Saved Videos"
            output_dir.mkdir(exist_ok=True)
            file_output = output_dir / f'Queens_Solve_{date}.gif'
            ani.save(file_output, writer="pillow")
        
        plt.show()

class Scraper():
    def __init__(self, date = None):
        self.date = date
        pass

    def get_queens_cells(self, headless = True):
        if self.date:
            date = self.date
        else:
            pacific_tz = pytz.timezone('America/Los_Angeles')
            date = datetime.datetime.now(pytz.utc).astimezone(pacific_tz)
            date = datetime.datetime.strftime(date, '%Y%m%d')
        
        file_dir = Path(__file__).parent
        queens_cells_path = file_dir / f"Saved Games/Queens_Board_{date}.html"

        print(queens_cells_path)
        if queens_cells_path.is_file():
            print('Existing File Found, Reading...')
            with open(queens_cells_path, 'r') as file:
                queens_cells_html = BeautifulSoup(file, 'html.parser')
        else:
            if self.date:
                raise Exception(FileNotFoundError)
            
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
                chrome_options.headless = True

            print('Starting Chrome...')
            driver = webdriver.Chrome(chrome_options)
            driver.get('https://www.linkedin.com/games/queens/')
            
            print('Loading Page...')
            iframe = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            driver.switch_to.frame(iframe)
            driver.find_element(By.ID, "launch-footer-start-button").click()
            
            print('Loading LinkedIn Queens...')
            queens_cells_html = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "queens-grid"))
            ).get_attribute('innerHTML')
            
            print('Retrieved Queens cells...')
            queens_cells_html = BeautifulSoup(queens_cells_html, 'html.parser')
            
            print('Writing File...')

            os.makedirs('Saved Games', exist_ok=True)
            with open(queens_cells_path, 'w') as file:
                file.write(str(queens_cells_html))
            
            print('Exiting Chrome...')
            driver.quit()
        
        queens_cells = set()
        id = 0
        for div in queens_cells_html.find_all('div'):
            label = div.get('aria-label')
            if label is None:
                continue
            matches = re.match("^.*color (?P<color>[A-Za-z ]+), row (?P<row>[0-9]+), column (?P<column>[0-9]+).*$", label)
            color = matches['color']
            row = int(matches['row'])
            column = int(matches['column'])
            queens_cells.add(Cell(id, color, row, column, 'available'))
            id += 1

        return queens_cells

if __name__ == '__main__':
    queens_scraper = Scraper(date = None)
    queens_cells = queens_scraper.get_queens_cells(headless=True)
    queens_solver = Solver(date = None)
    solved_board, solution = queens_solver.backtrack(Board({'available': queens_cells, 'selected': set(), 'eliminated': set()}), history=True)
    queens_solver.draw_solution(interval=175, save=True)
    print([(len(move['selected']), len(move['eliminated'])) for move in queens_solver.move_history])