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

class Cell:
    def __init__(self, id, color, row, column):
        self.id = id
        self.color = color
        self.row = row
        self.column = column

    def __eq__(self, other):
        return self.id == other.id
    
class Board: 
    def __init__(self, grid):
        self.grid = grid
        self.available = self.grid.copy()
        self.selected = []
        self.eliminated = []
        self.colors = set([cell.color for cell in self.available])

    def color_counts(self):
        color_counts = defaultdict(int)
        
        for cell in self.available:
            color_counts[cell.color] += 1

        return color_counts
    
    def get_priority_queue(self):
        color_counts = self.color_counts()
        min_count = min(color_counts.values())
        for color, count in color_counts.items():
            if count == min_count:
                best_color = color

        search_cells = []
        for cell in self.available:
            if cell.color == best_color:
                search_cells.append(cell)
        
        row_counts = defaultdict(int)
        column_counts = defaultdict(int)
        for cell in search_cells:
            row_counts[str(cell.row)] += 1
            column_counts[str(cell.column)] += 1
        
        queue = []
        for cell in search_cells:
            priority = row_counts[str(cell.row)]
            priority += column_counts[str(cell.column)]
            queue.append((cell, priority))
        
        queue = sorted(queue, key=lambda x: x[1], reverse=False)
        return queue
    
    def copy(self):
        new_board = Board(self.grid)
        new_board.grid = self.grid.copy()
        new_board.available = self.available.copy()
        new_board.selected = self.selected.copy()
        new_board.eliminated = self.eliminated.copy()
        return new_board

    def forecast_state(self, selected_cell):
        new_board = self.copy()
        new_board.selected.append(selected_cell)
        new_board.available.remove(selected_cell)
        cells_to_remove = []
        for cell in new_board.available:
            if cell.row == selected_cell.row or cell.column == selected_cell.column:
                cells_to_remove.append(cell)
                new_board.eliminated.append(cell)
            elif cell.color == selected_cell.color:
                cells_to_remove.append(cell)
                new_board.eliminated.append(cell)
            elif (cell.row, cell.column) in [
                (selected_cell.row+1, selected_cell.column+1), 
                (selected_cell.row+1, selected_cell.column-1), 
                (selected_cell.row-1, selected_cell.column+1), 
                (selected_cell.row-1, selected_cell.column-1)
                ]:
                cells_to_remove.append(cell)
                new_board.eliminated.append(cell)
            else:
                continue
        for cell in cells_to_remove:
            new_board.available.remove(cell)
        return new_board
    
    def display(self, scale = 3, margin = 0.5, keep = True):
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
        ax.set_xlim(1-margin, int((len(self.grid)) ** (1/2) + 1) * scale + margin)
        ax.set_ylim((int((len(self.grid)) ** (1/2) + 1) * scale + margin), (1-margin)) 
        ax.set_aspect('equal')
        for spine in ax.spines.values():
            spine.set_visible(False)
        for cell in self.grid:
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
    def __init__(self):
        self.move_history = []
        self.solution = None
        
    def solve(self, board, history = False):
        e_colors = set([cell.color for cell in board.eliminated])
        s_colors = set([cell.color for cell in board.selected])
        a_colors = set([cell.color for cell in board.available])
        if len(e_colors.difference(s_colors, a_colors)) > 0:
            if history:
                self.move_history.append({'selected': board.selected, 'eliminated': board.eliminated, 'status': 'Terminal Node Found, Backtracking...'})
            return board, False
        
        if len(board.selected) == len(board.colors):
            if history:
                self.move_history.append({'selected': board.selected, 'eliminated': board.eliminated, 'status': 'Solution Found!'})
            return board, True
        
        priority_queue = board.get_priority_queue()

        if history:
            self.move_history.append({'selected': board.selected, 'eliminated': board.eliminated, 'status': 'Searching...'})

        for selected_cell, _ in priority_queue:
            new_board, solution = self.solve(board.forecast_state(selected_cell), history=history)
            if solution:
                self.solution = new_board
                return new_board, True
        return new_board, False
    
    def draw_solution(self, scale = 3, margin = 0.5, interval = 50):
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
        def draw_board(ax, board_state, move_number):
            ax.cla()
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_xlim(1 - margin, int((len(self.solution.grid)) ** 0.5 + 1) * scale + margin)
            ax.set_ylim((int((len(self.solution.grid)) ** 0.5 + 1) * scale + margin), (1 - margin)) 
            ax.set_aspect('equal')

            for spine in ax.spines.values():
                spine.set_visible(False)

            for cell in self.solution.grid:
                ax.add_patch(plt.Rectangle((cell.column * scale, cell.row * scale),1 * scale, 1 * scale, facecolor=color_map[cell.color], edgecolor='black',linewidth=3 * scale/4))

            for cell in board_state['selected']:
                ax.text((cell.column + 0.5) * scale, (cell.row + 0.5) * scale, '\u265B', fontsize=5 * scale, ha='center', va='center')

            for cell in board_state['eliminated']:
                ax.text((cell.column + 0.5) * scale, (cell.row + 0.5) * scale, '\u00D7', fontsize=2 * scale, ha='center', va='center')

            ax.text(3, (int((len(self.solution.grid)) ** 0.5 + 1) * scale + margin), f'Move: {move_number + 1}, Status: {board_state["status"]}', fontsize=2.5*scale, ha='left', va='top')

        fig, ax = plt.subplots()
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0.15, hspace=0, wspace=0)
        draw_board(ax, self.move_history[0], 0)

        def update(val):
            if val >= len(self.move_history):
                val = len(self.move_history) - 1
            if self.move_history[val-1]['status'] == 'Terminal Node Found, Backtracking...': 
                time.sleep(0.1)
            status = draw_board(ax, self.move_history[val], val)
            fig.canvas.draw_idle()

        ani = animation.FuncAnimation(fig, update, frames = range(len(self.move_history)*2), interval=interval, repeat = False)
        pacific_tz = pytz.timezone('America/Los_Angeles')
        today = datetime.datetime.now(pytz.utc).astimezone(pacific_tz)
        today = datetime.datetime.strftime(today, '%Y%m%d')
        os.makedirs('Saved Videos', exist_ok=True)
        ani.save(f"Saved Videos/Queens_Solve_{today}.gif", writer="pillow")
        plt.show()

class Scraper():
    def __init__(self):
        pass

    def get_queens_grid(headless = True):
        pacific_tz = pytz.timezone('America/Los_Angeles')
        today = datetime.datetime.now(pytz.utc).astimezone(pacific_tz)
        today = datetime.datetime.strftime(today, '%Y%m%d')

        if os.path.exists(f'Saved Games/QueensBoard_{today}.html'):
            print('Existing File Found, Reading...')
            with open(f'Saved Games/QueensBoard_{today}.html', 'r') as file:
                queens_grid_html = BeautifulSoup(file, 'html.parser')
        else:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
                chrome_options.headless = True

            print('Starting Chrome...')
            driver = webdriver.Chrome(chrome_options)
            driver.get('https://www.linkedin.com/games/queens/')
            
            print('Loading Page...')
            iframe = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            driver.switch_to.frame(iframe)
            driver.find_element(By.ID, "launch-footer-start-button").click()
            
            print('Loading LinkedIn Queens...')
            queens_grid_html = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "queens-grid"))
            ).get_attribute('innerHTML')
            
            print('Retrieved Queens Grid...')
            queens_grid_html = BeautifulSoup(queens_grid_html, 'html.parser')
            
            print('Writing File...')
            os.makedirs('Saved Games', exist_ok=True)
            with open(f'Saved Games/Queens_Board_{today}.html', 'w') as file:
                file.write(str(queens_grid_html))
            
            print('Exiting Chrome...')
            driver.quit()
        
        queens_grid = []
        id = 0
        for div in queens_grid_html.find_all('div'):
            label = div.get('aria-label')
            if label is None:
                continue
            matches = re.match("^.*color (?P<color>[A-Za-z ]+), row (?P<row>[0-9]+), column (?P<column>[0-9]+).*$", label)
            color = matches['color']
            row = int(matches['row'])
            column = int(matches['column'])
            queens_grid.append(Cell(id, color, row, column))
            id += 1

        return queens_grid