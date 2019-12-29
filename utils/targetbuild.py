import math
from collections import namedtuple
import numpy as np


def signum(x: int) -> int:
    if x == 0:
        return 0

    return x / abs(x)

def get_euqlid(x, y):
    distance = 0.0
    for xc, yc in zip(x, y):
        distance += pow(xc - yc, 2)

    return math.sqrt(distance)

def get_nearest(point: tuple, array: list, edge: int) -> int:
    '''
    Returns the index of nearest point in array to given point
    :param array: list of all points
    :param point: point (C.O.)
    :param edge: max distance to be a neighbour
    :return: index of nearest point inn given list
    '''
    if len(array) < 1:
        return -1

    min_distance = edge
    nearest_point_index = -1
    ind = -1
    for arr_point in array:
        ind += 1
        distance = get_euqlid(arr_point, point)
        #СДЕЛАТЬ НОРМАЛЬНУЮ ПРОВЕРКУ НА ТУ ЖЕ САМУ ТОЧКУ
        if distance < min_distance:# and distance != 0:
            min_distance = distance
            nearest_point_index = ind

    return nearest_point_index

class TargetMap:
    '''

    :param size: named tuple with x and y field, define size of resulting image
    :param field_size: receprive field of dnn, define size of squares in image
    '''
    def __init__(self, size: namedtuple, field_size: int) -> None:
        self.size = size
        self.target_map = np.zeros((size.x, size.y, 1))
        self.field_size = field_size
    def changeCell(self, point: namedtuple, delta: int) -> np.array:
        #INSPECT INDEXES
        border = int(self.field_size / 2)
        for i in range(-border, border):
            for j in range(-border, border):
                self.target_map[point.x + i][point.y + j][0] += delta

        return self.target_map

    def addCell(self, point: namedtuple):
        return self.changeCell(point, 1)

    def eraseCell(self, point: namedtuple):
        return self.changeCell(point, -1)

    def resize(self, new_size: namedtuple):
        #INSPECT INDEXES WITH ODD NUMBERS
        padx = int((new_size.x - self.size.x) / 2)
        if padx < 0:
            self.target_map = self.target_map[padx:-padx, :, :]
            padx = 0
        pady = int((new_size.y - self.size.y) / 2)
        if pady < 0:
            self.target_map = self.target_map[:, pady:-pady, :]
            pady = 0

        self.target_map = np.pad(self.target_map, ((padx, padx), (pady, pady), (0, 0)), mode='constant')