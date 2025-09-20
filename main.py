from queens import Solver, Scraper, Board

if __name__ == '__main__':
    queens_scraper = Scraper(date = None)
    queens_grid = queens_scraper.get_queens_grid(headless=False)
    queens_solver = Solver(date = None)
    solved_board, solution = queens_solver.solve(Board(queens_grid), history=True)
    queens_solver.draw_solution(scale = 3, interval=50, save=True)