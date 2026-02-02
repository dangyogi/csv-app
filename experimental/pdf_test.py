# pdf_test.py

from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, portrait, letter, inch


def hello(c):
    x = 20
    y = 770
    for i in range(6):  # 0 comes out as thin gray
        c.drawString(x, y - 20*i, str(i))
        c.setLineWidth(i)
        c.line(x + 50, y - 20*i, x + 150, y - 20*i)
    y -= 100
    c.setFont("Helvetica", 100)
    y -= 100
    c.setLineWidth(0)
    test_str = "Hfglpy_|;'\",/\\"
    width = c.stringWidth(test_str)        # 530.8 (~38% of size/char) for "Hfglpy_|;'\",/\\" at size 100
    print(f"{len(test_str)=}, {width=}")
    c.drawString(x, y, test_str)
    c.line(x - 10, y, 600, y)              # underneath (bottom of chars, not counting decenders, just below y)
                                           #   20% of size for decenders, below y
    c.line(x - 10, y + 100, 600, y + 100)  # on top (well above highest char),
                                           # highest char about 71% of size above y
    c.line(x, y - 50, x, y + 100)          # left (str starts 1/2 space between letters from x)
    c.setLineWidth(5)
    c.line(x + 200, y - 9.95, x + 272, y - 9.95)  # matches underscore char:
                                                  #   5% of font size for line width,
                                                  #   9.95% of font size below y pos of text

    y -= 150
    c.setLineWidth(5)                      # doesn't affect normal drawString (next line)
    c.drawString(x, y, test_str)
    c.setLineWidth(0)
    c.line(x - 10, y, 600, y)              # underneath (bottom of chars, not counting decenders, just below y)
    c.line(x - 10, y + 100, 600, y + 100)  # on top (well above highest char)
    c.line(x, y - 50, x, y + 100)          # left (str starts 1/2 space between letters from x)

def sizing(c):
    # "gl" sizings as a percentage of fontsize:
    #
    # y values:
    #   top of "l"                         =  71.8%
    #   top of "g"                         =  54%
    #   bottom of "l"                      =   0%
    #   bottom of "g" (excluding decender) =  -1%
    #   bottom of "g" decender             = -22%
    #
    # x values:
    #   left of "g"                        =   4%
    #   right of "g"                       =  50.02%
    #   right of "l"                       =  74.8%
    #   right of stringWidth("gl")         =  83.4%
    #   stringWidth("g")           360.288 =  55.6%
    #   stringWidth("l")           143.856 =  22.2%

    # 72 * 9 == 648
    scale_fontsize = 8
    fontsize = 648
    y_bottom = Height - (scale_fontsize * 1.5) - fontsize * 0.90  # 132
    x_left = 20
    c.setLineWidth(0)
    c.setStrokeColorRGB(0, 0, 1)
    for i in range(-25, 101, 1):    # blue 1% lines
        # horz line
        c.line(x_left - scale_fontsize * 0.5, y_bottom + i*(fontsize * 0.01), 
               Width,                         y_bottom + i*(fontsize * 0.01)) 
        if 0 <= i <= 92:
            # vert line
            c.line(x_left - scale_fontsize * 0.25 + i*(fontsize * 0.01), scale_fontsize,
                   x_left - scale_fontsize * 0.25 + i*(fontsize * 0.01), Height)
    c.setStrokeColorRGB(0, 1, 0)
    for i in range(-25, 101, 5):    # green 5% lines
        # horz line
        c.line(x_left - scale_fontsize * 0.5, y_bottom + i*(fontsize * 0.01), 
               Width,                         y_bottom + i*(fontsize * 0.01)) 
        if 0 <= i <= 92:
            # vert line
            c.line(x_left - scale_fontsize * 0.25 + i*(fontsize * 0.01), scale_fontsize,
                   x_left - scale_fontsize * 0.25 + i*(fontsize * 0.01), Height)
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(1, 0, 0)
    c.setStrokeColorRGB(1, 0, 0)
    for i in range(-20, 101, 10):   # red 10% lines, labeled 
        # vertical scale
        c.drawString(0, y_bottom + i*(fontsize * 0.01) - scale_fontsize * 0.5, f"{i:3}")
        # horz line
        c.line(x_left - scale_fontsize * 0.5, y_bottom + i*(fontsize * 0.01), 
               Width,                         y_bottom + i*(fontsize * 0.01)) 
        # horz scale
        if 0 <= i <= 92:
            c.drawString(x_left - scale_fontsize * 0.8 + i*(fontsize * 0.01),
                         0, f"{i:2}")
            # vert line
            c.line(x_left - scale_fontsize * 0.25 + i*(fontsize * 0.01), scale_fontsize,
                   x_left - scale_fontsize * 0.25 + i*(fontsize * 0.01), Height)
    c.setFont("Helvetica", 648)
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(0, 0, 0)
    print("width of space", c.stringWidth(" "))  #   180.144 (27.8% of fontsize)
    test_str = "gI"
    print("width of", test_str, c.stringWidth(test_str))   # 540.432
    g_width = c.stringWidth("g")
    print("width of", "g", g_width)              #   360.288
    print("width of", "l", c.stringWidth("l"))   # + 143.856
                                                 # ---------
                                                 #   504.144 (93.29% of 540.432)
    if False:
        c.drawString(x_left, y_bottom, test_str)
    else:
        c.drawString(x_left, y_bottom, "g")
        c.drawString(x_left + g_width, y_bottom, "l")  # "l" is 3.3% to the left of "gl"

def fontsizes(c):
    y = 700
    for size in range(8, 30):
        c.setFont("Helvetica", size)
        c.drawString(10, y, f"{size:2}: Treasurer's Report Cash Flow Donations")
        c.setFont("Helvetica-Bold", size)
        c.drawString(310, y, f"{size:2}: Treasurer's Report Cash Flow Donations")
        y -= size

def run():
    global Width, Height
    pagesize = portrait(letter)  # in points (1/72"), portrait is 612 x 792
    print(f"{pagesize=}")

    #pagesize = landscape(letter)

    Width, Height = pagesize

    path = Path("~/storage/downloads/fontsizes.pdf")
    c = canvas.Canvas(str(path.expanduser()), pagesize=pagesize)

   #hello(c)
   #sizing(c)
    fontsizes(c)

    # clears all settings (colors, fonts, etc).  These must be re-established.
    c.showPage()

    c.save()


if __name__ == "__main__":
    run()
