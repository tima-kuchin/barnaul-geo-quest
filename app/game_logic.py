import os
import random
import json

# Загрузка координат из JSON файла
if os.path.exists('valid_coordinates.json'):
    with open('valid_coordinates.json', 'r') as f:
        coordinates = json.load(f)
else:
    coordinates = []

class GameSession:
    def __init__(self):
        self.used_coordinates = []

    def get_random_coordinates(self):
        available_coords = [coord for coord in coordinates if coord not in self.used_coordinates]
        if not available_coords:
            self.used_coordinates = []
            available_coords = coordinates.copy()
        coord = random.choice(available_coords)
        self.used_coordinates.append(coord)
        return coord

# Экземпляр для использования в приложении
session = GameSession()
