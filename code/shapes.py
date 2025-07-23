from OpenGL.GL import *
from OpenGL.GLU import *
from contextlib import contextmanager
from freetype import *

@contextmanager
def glmatrix():
    glPushMatrix()
    yield
    glPopMatrix()

def square_geometry():
    glBegin(GL_TRIANGLE_FAN)
    glNormal3f(0, 0, 1)
    #if texture: 
    glTexCoord2f(0,1)
    glVertex3f(-0.5, -0.5, 0.5)
    #if texture: 
    glTexCoord2f(1,1)
    glVertex3f(0.5, -0.5, 0.5)
    #if texture: 
    #glTexCoord2f(1,1)
    glTexCoord2f(1,0)
    glVertex3f(0.5, 0.5, 0.5)
    #if texture: 
    glTexCoord2f(0,0)
    glVertex3f(-0.5, 0.5, 0.5)
    glEnd()

def square_lines():
    glBegin(GL_LINE_LOOP)
    glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(0.5, -0.5, 0.5)
    glEnd() 


def text_square(bgfill, fgfill, character):
    glColor4f(*bgfill)
    glyph_size = character.size
    #char_size = character.glyph.width, character.glyph.height
    tex_max_dim = float(max(*glyph_size))
    #tex_max_dim = float(max(character.glyph.metrics.width, character.glyph.metrics.height))
    #print(character.glyph.get_glyph().get_cbox(FT_GLYPH_BBOX_PIXELS))
    #print(character.letter, (character.glyph.metrics.width,character.glyph.metrics.height), character.size)
    #glyph_size = character.bitmap.width, character.bitmap.rows
    #tex_max_dim = float(max(*character.size))
    #tex_max_dim = float(max(*char_size))
    scale = 0.6
    try:
        tex_normalized_size = (glyph_size[0]/tex_max_dim)*scale, (glyph_size[1]/tex_max_dim)*scale
    except:
        tex_normalized_size = 1, 1
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, character.texture())
    glTexEnvfv(GL_TEXTURE_ENV, GL_TEXTURE_ENV_COLOR, fgfill)
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_COMBINE)
    glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_INTERPOLATE) # interpolate using alpha
    glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_RGB, GL_PREVIOUS) # take background RGB from previous color (glColor4f)
    glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_RGB, GL_SRC_COLOR)
    glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_RGB, GL_CONSTANT) # take background RGB from constant color (GL_TEXTURE_ENV_COLOR)
    glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_RGB, GL_SRC_COLOR)#GL_ONE_MINUS_SRC_COLOR)#
    #glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_RGB, GL_ONE_MINUS_SRC_COLOR)#
    glTexEnvi(GL_TEXTURE_ENV, GL_SRC2_RGB, GL_TEXTURE) # take alpha channel from texture
    glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND2_RGB, GL_ONE_MINUS_SRC_ALPHA) # interpolate against 1-alpha
    glBegin(GL_TRIANGLE_FAN)
    uv_offset = (1.0-tex_normalized_size[0])/2.0, (1.0-tex_normalized_size[1])/2.0
    glNormal3f(0, 0, 1)
    #if texture: 
    #glTexCoord2f(0-uv_offset[0],1+uv_offset[1])
    glTexCoord2f(0-uv_offset[0],1+uv_offset[1])
    glVertex3f(-0.5, -0.5, 0.5)
    #if texture: 
    glTexCoord2f(1+uv_offset[0],1+uv_offset[1])
    glVertex3f(0.5, -0.5, 0.5)
    #if texture: 
    #glTexCoord2f(1,1)
    glTexCoord2f(1+uv_offset[0],0-uv_offset[1])
    glVertex3f(0.5, 0.5, 0.5)
    #if texture: 
    glTexCoord2f(0-uv_offset[0],0-uv_offset[1])
    glVertex3f(-0.5, 0.5, 0.5)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glLineWidth(6)
    glColor4f(0.1,0.1,0.1,1)  #/ Set the color for the square.
    square_lines()
    glLineWidth(1)



def square(fill=None, stroke=None, stroke_width=1, texture=None):
    if texture or (fill and fill[3] < 1):
        #glDisable(GL_DEPTH_TEST)
        #glEnable(GL_CULL_FACE)
        #glCullFace(GL_BACK)
        #glAlphaFunc(GL_GREATER, 0.1)
        #glEnable(GL_ALPHA_TEST)
        pass
    if fill or texture:
        if fill and not texture:
            glColor4f(*fill)
            square_geometry()
            glColor4f(1, 1, 1, 1);
        if texture and not fill:
            #glEnable(GL_BLEND)
            #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA) # why no transparency, wrong loading of texture?
            #glBlendFunc(GL_ADD,)# is this what this does, change the op to add
            glColor4f(0, 1, 0, 1)# * this is multiplied by tex value - can we have another op?
            glEnable(GL_TEXTURE_2D)
            glTexEnvfv(GL_TEXTURE_ENV, GL_TEXTURE_ENV_COLOR, (1,0,0,1))#GL_REPLACE)
            glBindTexture(GL_TEXTURE_2D, texture)
            glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_COMBINE)#GL_COMBINE)#GL_REPLACE)
            glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_INTERPOLATE)#GL_REPLACE)
            glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_RGB, GL_PREVIOUS)#GL_REPLACE)
            glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_RGB, GL_SRC_COLOR)#GL_REPLACE)
            glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_RGB, GL_CONSTANT)#GL_REPLACE)
            glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_RGB, GL_SRC_COLOR)#GL_REPLACE)
            glTexEnvi(GL_TEXTURE_ENV, GL_SRC2_RGB, GL_TEXTURE)#GL_REPLACE)
            glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND2_RGB, GL_ONE_MINUS_SRC_ALPHA)#GL_SRC_ALPHA)#GL_REPLACE)
            #glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_ALPHA, GL_ONE_MINUS_SRC_ALPHA)#GL_REPLACE)
            square_geometry()
            glDisable(GL_TEXTURE_2D)
            #glBindTexture(GL_TEXTURE_2D, 0)
            #glDisable(GL_BLEND)
        if texture and fill:
            #glEnable(GL_BLEND)
            #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            #glBlendEquation(GL_FUNC_ADD)
            square(fill=fill)
            square(texture=texture)
            #glBlendFunc(GL_ONE_MINUS_DST_ALPHA, GL_SRC_COLOR)
            #glBlendEquation(GL_FUNC_ADD)
            #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            #glBlendEquation(GL_FUNC_ADD)
            #glColor4f(1, 0, 0, 1);
            #if fill:
            #    glBlendColor(*fill)
            #glDisable(GL_BLEND);
    if texture or (fill and fill[3] < 1):
        #glEnable(GL_DEPTH_TEST)
        #glDisable(GL_CULL_FACE)
        #glDisable(GL_ALPHA_TEST)
        pass
    if stroke:
        glLineWidth(stroke_width)
        glColor4f(*stroke)  #/ Set the color for the square.
        square_lines()
        glLineWidth(1)

def plane(width, height, fill=None, stroke=None, stroke_width=1, texture=None):
    for w in range(width):
        for h in range(height):
            with glmatrix():
                glTranslatef(w, h, 0)
                square(fill, stroke, stroke_width, texture)

def text_cube(*args):
    with glmatrix():
        glTranslatef(0.5,0.5,0.5)
        with glmatrix(): # front face
            text_square(*args)
        with glmatrix(): # right face
            glRotatef(90, 0, 1, 0)
            text_square(*args)
        with glmatrix(): # top face
            glRotatef(-90, 1, 0, 0)
            text_square(*args)
        with glmatrix(): # back face
            glRotatef(180, 0, 1, 0)
            text_square(*args)
        with glmatrix(): # left face
            glRotatef(-90, 0, 1, 0)
            text_square(*args)
        with glmatrix(): # bottom face
            glRotatef(90, 1, 0, 0)
            text_square(*args)


def cube(fill=None, stroke=None, stroke_width=1, texture=None):
    with glmatrix():
        glTranslatef(0.5,0.5,0.5)
        with glmatrix(): # front face
            square(fill, stroke, stroke_width, texture)
        with glmatrix(): # right face
            glRotatef(90, 0, 1, 0)
            square(fill, stroke, stroke_width, texture)
        with glmatrix(): # top face
            glRotatef(-90, 1, 0, 0)
            square(fill, stroke, stroke_width, texture)
        with glmatrix(): # back face
            glRotatef(180, 0, 1, 0)
            square(fill, stroke, stroke_width, texture)
        with glmatrix(): # left face
            glRotatef(-90, 0, 1, 0)
            square(fill, stroke, stroke_width, texture)
        with glmatrix(): # bottom face
            glRotatef(90, 1, 0, 0)
            square(fill, stroke, stroke_width, texture)

def axis():
    glLineWidth(8)
    glBegin(GL_LINES)
    #x
    glColor3f(1,0,0)
    glVertex3f(0, 0, 0)
    glVertex3f(2.5, 0, 0)
    #y
    glColor3f(0,1,0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 2.5, 0)
    #z
    glColor3f(0,0,1)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, 2.5)
    glEnd()
    glLineWidth(1)

