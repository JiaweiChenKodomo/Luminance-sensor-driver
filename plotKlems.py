#!/usr/bin/env python3

import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.patches import Circle
#from matplotlib.ticker import LinearLocator
import numpy as np
#from time import sleep

def cart2pol(x, y):
    rho = np.sqrt(x**2 + y**2)
    phi = np.arctan2(y, x)
    return rho, phi

def assignKlemsPatch():
    """Translated from Alex's MATLAB code witn major overhauls on the Klems patch assignment
    algorithm.
    In this code, the klems basis data in the outgoing direction
    is projected onto a plane, with the observer facing the outgoing direction.
    Jiawei, 2021
    """

    """Picture dimensions"""
    Y = 480;
    X = 720;
    rad = 227;
    """ Must calculate the focual length in pixels. This is the projection
    equation for a equi-solid angle, circular fisheye lens expressing the
    focal length in terms of the radius and pixel distance at that radius."""
    fpixel = rad / (2 * np.sin(np.pi / 4))

    xShift = X / 2;
    yShift = Y / 2;

    """Create x and y matrices for the pixels"""
    xBase = np.arange(X)
    yBase = np.arange(Y)
    x, y = np.meshgrid(xBase, yBase)

    """Shift the x and y matrices to align the origin as the center of the photo
    measurement."""
    x = x - xShift
    y = y - yShift

    """Convert from cartesian to polar coordinates. These are now the base theta
    and rho values for the associated pixels in the matrices position"""
    rho, theta = cart2pol(x, y)

    """Process rho and theta for proper orientations
    rho: must zero out pixels not in fisheye exposure
    theta: must make all thetas in [0,2*pi]"""
    for ii in range(Y):
        for jj in range(X):
            if rho[ii, jj] > rad:
                rho[ii, jj] = -1;

    for ii in range(Y):
        for jj in range(X):
            if theta[ii, jj] < 0:
                theta[ii, jj] += 2 * np.pi

    """Populate the Rinner"""
    Rinner = np.zeros(9)

    """Some holder constants"""
    segments = [1,8,16,20,24,24,24,16,12]
    starts = [1,2,10,26,46,70,94,118,134]
    stops = [1,9,25,45,69,93,117,133,145]

    """'angles' is precisely what needs changing"""
    ang = [0,5,15,25,35,45,55,65,75,90]
    angles = [(2 * fpixel * np.sin(elem / 2 * np.pi / 180)) / rad for elem in ang]

    """Loop through each ring"""
    for jj in range(9):
        """Ring Specific constants"""
        Rinner[jj] = angles[jj] * rad

    """Make a klems basis specifier"""
    klems = np.zeros((Y,X)) - 1

    """This loop assigns the klems value to each pixel explicitly"""
    for ii in range(Y):
        for jj in range(X):
            # If the radius is larger than the out-most ring, directly set to initial value.
            # If the radius is 0, set to the first patch.
            if rho[ii, jj] >= 0:
                ringNo = np.searchsorted(Rinner, rho[ii, jj], side='right') - 1
                if ringNo == 0:
                    klems[ii, jj] = 0
                else:
                    # Ring info
                    ringStartPatch = starts[ringNo] - 1
                    ringEndPatch = stops[ringNo] - 1
                    segs = segments[ringNo]
                    segArc = 2 * np.pi / segs
                    # The treatment of theta determines the direction of the projection
                    thetaStart = (segArc / 2) + np.pi
                    patchNo = 0
                    if thetaStart >= theta[ii, jj]:
                        patchNo = ringStartPatch + int((thetaStart - theta[ii, jj]) / segArc)
                    else:
                        patchNo = ringStartPatch + int((thetaStart + 2 * np.pi - theta[ii, jj]) / segArc)
                    klems[ii, jj] = patchNo
    return klems

def drawOutline(ax):
    """Draw the outline of all the patches.
    ax : matplotlib.axes.Axes
        The axes object to draw the ellipse into.
    Jiawei, 2021
    """
    """Picture dimensions"""
    Y = 480;
    X = 720;
    rad = 227;
    """ Must calculate the focual length in pixels. This is the projection
    equation for a equi-solid angle, circular fisheye lens expressing the
    focal length in terms of the radius and pixel distance at that radius."""
    fpixel = rad / (2 * np.sin(np.pi / 4))

    xShift = X / 2;
    yShift = Y / 2;

    """Populate the Rinner"""
    Rinner = np.zeros(9)
    Router = np.zeros(9)

    """Some holder constants"""
    segments = [1,8,16,20,24,24,24,16,12]
    starts = [1,2,10,26,46,70,94,118,134]
    stops = [1,9,25,45,69,93,117,133,145]

    """'angles' is precisely what needs changing"""
    ang = [0,5,15,25,35,45,55,65,75,90]
    angles = [(2 * fpixel * np.sin(elem / 2 * np.pi / 180)) / rad for elem in ang]

    """Loop through each ring"""
    for jj in range(9):
        """Ring Specific constants"""
        Rinner[jj] = angles[jj] * rad
        Router[jj] = angles[jj + 1] * rad

    """Draw circles"""
    for r_circ in Router:
        circle = Circle((xShift, yShift), radius = r_circ, fill = 0)
        ax.add_patch(circle)

    """Draw lines to form the patches. Only need to start from the second ring."""
    for ring_no in range(8):
        segs = segments[ring_no + 1]
        segArc = 2 * np.pi / segs
        r_in = Rinner[ring_no + 1]
        r_out = Router[ring_no + 1]
        for line_no in range(segs):
            line_ang = (line_no - 0.5) * segArc
            x = [r_in * np.cos(line_ang) + xShift, r_out * np.cos(line_ang) + xShift]
            y = [r_in * np.sin(line_ang) + yShift, r_out * np.sin(line_ang) + yShift]
            ax.plot(x, y, color = 'k')
    return 0


def plotKlems(klems_vec, klems_idx, addPatch = 1, addOutline = 1, rangeMax = None, rangeMin = None, viewOutside = 1, left_shift = 3, addLegend = 1, blocking = True, time_sec = 1.0):
    """Translated from Alex's MATLAB code witn major overhauls on the Klems patch assignment
    algorithm.
    In this code, the klems basis data in the outgoing direction
    is projected onto a plane, with the observer facing the outgoing direction.

    klems_vec: the 145 * 1 vector of the readings in the Klems basis. Given as
    a numpy array or a list.
    klems_idx: the pixel-patch mapping array. Assigns each pixel in the figure a Klems patch.
    addPatch: if == 1, add the patch number to the figure.
    addOutline: if == 1, add outlines of the patches.
    rangeMax: specifies the maximum of the colorbar.
    rangeMin: specifies the minimum of the color bar.
    viewOutside: if == 1, the projection is in the direction following the outside light into the room.
    left_shift: shifts the patch number left a bit for better visualization.
    Jiawei, 2021.
    """

    if rangeMax is None:
        rangeMax = np.max(klems_vec)

    if rangeMin is None:
        rangeMin = np.min(klems_vec)

    """Picture dimensions"""
    Y = 480;
    X = 720;
    rad = 227;
    """ Must calculate the focual length in pixels. This is the projection
    equation for a equi-solid angle, circular fisheye lens expressing the
    focal length in terms of the radius and pixel distance at that radius."""
    fpixel = rad / (2 * np.sin(np.pi / 4))
    xShift = X / 2;
    yShift = Y / 2;

    """Create x and y matrices for the pixels"""
    xBase = np.arange(X)
    yBase = np.arange(Y)
    x, y = np.meshgrid(xBase, yBase)

    """Make a klems basis specifier"""
    klems = np.zeros((Y,X))

    """This loop assigns the klems value to each pixel explicitly"""
    for ii in range(Y):
        for jj in range(X):
            if klems_idx[ii, jj] >= 0:
                klems[ii, jj] = klems_vec[int(klems_idx[ii, jj])]
            else:
                klems[ii, jj] = np.nan

    """Make the plot"""
    fig, ax = plt.subplots()
    surf = ax.pcolormesh(x, y, klems, cmap=cm.hot, vmin = rangeMin, vmax = rangeMax, linewidth=0, antialiased=0)

    # Add a color bar which maps values to colors.
    if addLegend:
        cbar = fig.colorbar(surf)
        cbar.ax.set_ylabel('Luminance (nit)')

    if addPatch:
        """Some holder constants"""
        segments = [1,8,16,20,24,24,24,16,12]
        starts = [1,2,10,26,46,70,94,118,134]
        stops = [1,9,25,45,69,93,117,133,145]

        """'angles' is precisely what needs changing"""
        ang = [0,5,15,25,35,45,55,65,75,90]
        angles = [(2 * fpixel * np.sin(elem / 2 * np.pi / 180)) / rad for elem in ang]

        for k in range(145):
            ringNo = np.searchsorted(stops, k, side='right')
            r_no = (angles[ringNo] + angles[ringNo + 1]) * rad / 2;
            patchNo = k - starts[ringNo] + 1
            segs = segments[ringNo]
            segArc = 2 * np.pi / segs
            theta_no = -patchNo * segArc + np.pi;
            x_no = r_no * np.cos(theta_no)
            y_no = r_no * np.sin(theta_no)
            plt.text(x_no + xShift - left_shift, y_no + yShift, str(k + 1))

    if addOutline:
        drawOutline(ax)

    if not viewOutside:
        ax.invert_xaxis()

    if blocking:
        plt.show()
    else:
        plt.draw()
        plt.pause(time_sec)
        plt.close()


def main():
    klems_idx = assignKlemsPatch()
    klems_vec = np.arange(145)
    klems_vec2 = [290 - aa * 2 for aa in range(145)]
    klems_vec3 = [10 if aa%2 == 0 else 20 for aa in range(145)]
    klems_vec4 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4,
    5, 5, 5, 5, 5, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 2,
    2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 2, 2,
    2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 9, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 11,
    11, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11,
    11, 11, 7, 7, 7, 7, 8, 8, 8, 8, 9, 9, 10, 10, 10, 11, 11, 11, 7, 7, 7, 8,
    8, 8, 9, 9, 10, 10, 11, 11]
    klems_vec5 = [aa**2 for aa in klems_vec4]
    #klems_vec6 = [0	1	0	1	0	1	0	1	0	0	0	1	1	0	0	0	0	0	0	0	0	0	0	1	0	0	1	0	0	1	0	1	0	0	1	0	1	0	0	1	0	1	0	0	1	1	0	0	0	0	0	0	1	0	0	0	0	0	0	0	0	0	0	1	1	0	0	0	0	1	1	0	0	0	0	0	0	0	0	0	0	0	1	0	0	0	0	1	0	0	0	0	0	0	0	1	0	1	0	0	0	1	0	1	0	0	0	1	0	1	0	0	0	1	0	1	0	0	0	1	0	0	0	0	0	0	0	1	0	0	0	0	0	0	0	1	0	0	0	0	1	0	0	0	0];
    #plotKlems(klems_vec, klems_idx)
    #plotKlems(klems_vec2, klems_idx)
    #plotKlems(klems_vec3, klems_idx, 1, 1, None, 0.0, 0, -3, 0)
    plotKlems(klems_vec5, klems_idx, 1, 1, None, 0.0, 0, -3, 0)
    #plotKlems(klems_vec6, klems_idx, 1, 1, None, 0.0, 0, -3, 0)


if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()
