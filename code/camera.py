from math import radians, cos, sin
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *

"""
minecraft coordinate system
https://minecraft.fandom.com/wiki/Coordinates

world block coordinates are the lower northwest corner of the block
+z is south
+y is up
+x is east

(this seems to be the same as OpenGL)

"""

SQRT2 = 2 ** .5
render_distance_chunks = 12

def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0: 
        return v
    return v / norm

class Camera:
    def __init__(self, width, height, x, y, z, yaw=-90.0, pitch=0.0, world_up=None):
        self.x = x
        self.y = y
        self.z = z
        self.world_up = world_up or np.array([0,1,0])
        self.width = width
        self.height = height
        self.yaw = yaw
        self.pitch = pitch

    def __str__(self):
        return "Camera [x:{}, y:{}, z:{}, pitch: {}, yaw: {}]".format(self.x, self.y, self.z, self.pitch, self.yaw)

    @property
    def front(self):
        return np.array([cos(radians(self.yaw)) * cos(radians(self.pitch)),\
                         sin(radians(self.pitch)),\
                         sin(radians(self.yaw)) * cos(radians(self.pitch))])

    @property
    def right(self):
        return normalize(np.cross(self.front, self.world_up))

    @property
    def position(self):
        return np.array([self.x, self.y, self.z])

    @property
    def up(self):
        return normalize(np.cross(self.right, self.front));

    def move(self, x=0, y=0, z=0, yaw=0, pitch=0):
        self.x += x
        self.y += y
        self.z += z
        self.yaw = (self.yaw + yaw) % 360
        self.pitch = (self.pitch + pitch) % 360
        self.apply()

    def apply(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = 1366/768.0 # current
        #aspect = self.width/float(self.height or 1) # old?
        gluPerspective(70, aspect, .05, (render_distance_chunks * 16) * SQRT2) #old?
        #gluPerspective(100, aspect, .01, (render_distance_chunks * 16) * SQRT2) #current
        center = self.position + self.front
        gluLookAt(self.x, self.y, self.z,\
                  center[0], center[1], center[2],\
                  self.up[0], self.up[1], self.up[2])
        glMatrixMode(GL_MODELVIEW)
