# Copyright 2019 by Kurt Rathjen. All Rights Reserved.
#
# This library is free software: you can redistribute it and/or modify it 
# under the terms of the GNU Lesser General Public License as published by 
# the Free Software Foundation, either version 3 of the License, or 
# (at your option) any later version. This library is distributed in the 
# hope that it will be useful, but WITHOUT ANY WARRANTY; without even the 
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Lesser General Public License for more details.
# You should have received a copy of the GNU Lesser General Public
# License along with this library. If not, see <http://www.gnu.org/licenses/>.

import os
import logging

from studioqt import QtGui
from studioqt import QtCore
from studioqt import QtWidgets

import studioqt
import studiolibrarymaya
import studiolibrary.widgets

try:
    import mutils
    import mutils.gui
    import maya.cmds
except ImportError as error:
    print(error)

__all__ = [
    "BaseCreateWidget",
]

logger = logging.getLogger(__name__)


class BaseCreateWidget(QtWidgets.QWidget):

    """Base create widget for creating new maya items."""

    def __init__(self, item, parent=None):
        """
        :type item: studiolibrarymaya.BaseItem
        :type parent: QtWidgets.QWidget
        """
        QtWidgets.QWidget.__init__(self, parent)
        self.setObjectName("studioLibraryMayaCreateWidget")

        self.setWindowTitle("Create Item")

        studioqt.loadUi(self)

        self._item = None
        self._iconPath = ""
        self._scriptJob = None
        self._focusWidget = None
        self._optionsWidget = None
        self._libraryWindow = None

        text = "Click to capture a thumbnail from the current model panel.\n" \
               "CTRL + Click to show the capture window for better framing."

        self.ui.thumbnailButton.setToolTip(text)

        self.ui.acceptButton.clicked.connect(self.accept)
        self.ui.thumbnailButton.clicked.connect(self.thumbnailCapture)
        self.ui.browseFolderButton.clicked.connect(self.browseFolder)
        self.ui.selectionSetButton.clicked.connect(self.showSelectionSetsMenu)

        self.setCaptureMenuEnabled(True)

        try:
            self.selectionChanged()
            self.setScriptJobEnabled(True)
        except NameError as error:
            logger.exception(error)

        self.setItem(item)
        self.updateContains()
        self.updateThumbnailSize()

    def setLibraryWindow(self, libraryWindow):
        """
        Set the library widget for the item.
        
        :type libraryWindow: studiolibrary.LibraryWindow
        :rtype: None
        """
        self.item().setLibraryWindow(libraryWindow)

    def libraryWindow(self):
        """
        Return the library widget for the item.

        :rtype: libraryWindow: studiolibrary.LibraryWindow
        """
        return self.item().libraryWindow()

    def item(self):
        """
        Return the library item to be created.

        :rtype: studiolibrarymaya.BaseItem
        """
        return self._item

    def setItem(self, item):
        """
        Set the base item to be created.

        :type item: studiolibrarymaya.BaseItem
        """
        self._item = item

        if hasattr(self.ui, "optionsFrame"):
            options = item.options()
            if options:
                optionsWidget = studiolibrary.widgets.OptionsWidget(self)
                optionsWidget.setOptions(item.saveOptions())
                optionsWidget.setValidator(item.saveValidator)
                self.ui.optionsFrame.layout().addWidget(optionsWidget)
                self._optionsWidget = optionsWidget
            else:
                self.ui.optionsFrame.setVisible(False)

    def iconPath(self):
        """
        Return the icon path to be used for the thumbnail.

        :rtype str
        """
        return self._iconPath

    def setIconPath(self, path):
        """
        Set the icon path to be used for the thumbnail.

        :type path: str
        :rtype: None
        """
        self._iconPath = path
        icon = QtGui.QIcon(QtGui.QPixmap(path))
        self.setIcon(icon)
        self.updateThumbnailSize()

    def setIcon(self, icon):
        """
        Set the icon for the create widget thumbnail.

        :type icon: QtGui.QIcon
        """
        self.ui.thumbnailButton.setIcon(icon)
        self.ui.thumbnailButton.setIconSize(QtCore.QSize(200, 200))
        self.ui.thumbnailButton.setText("")

    def settings(self):
        """
        Return the settings object for saving the state of the widget.

        :rtype: studiolibrary.Settings
        """
        return studiolibrarymaya.settings()

    def saveSettings(self):
        """
        Save the current state of the widget to disc.

        :rtype: None
        """
        data = self.settings()
        studiolibrarymaya.saveSettings(data)

    def showSelectionSetsMenu(self):
        """
        Show the selection sets menu for the current folder path.

        :rtype: None
        """
        import setsmenu

        path = self.folderPath()
        position = QtGui.QCursor().pos()
        libraryWindow = self.libraryWindow()

        menu = setsmenu.SetsMenu.fromPath(path, libraryWindow=libraryWindow)
        menu.exec_(position)

    def close(self):
        """
        Overriding the close method so that we can disable the script job.

        :rtype: None
        """
        self.setScriptJobEnabled(False)
        QtWidgets.QWidget.close(self)

    def scriptJob(self):
        """
        Return the script job object used when the users selection changes.

        :rtype: mutils.ScriptJob
        """
        return self._scriptJob

    def setScriptJobEnabled(self, enable):
        """
        Enable the script job used when the users selection changes.

        :rtype: None
        """
        if enable:
            if not self._scriptJob:
                event = ['SelectionChanged', self.selectionChanged]
                self._scriptJob = mutils.ScriptJob(event=event)
        else:
            sj = self.scriptJob()
            if sj:
                sj.kill()
            self._scriptJob = None

    def resizeEvent(self, event):
        """
        Overriding to adjust the image size when the widget changes size.

        :type event: QtCore.QSizeEvent
        """
        self.updateThumbnailSize()

    def updateThumbnailSize(self):
        """
        Update the thumbnail button to the size of the widget.

        :rtype: None
        """
        if hasattr(self.ui, "thumbnailButton"):
            width = self.width() - 10
            if width > 250:
                width = 250

            size = QtCore.QSize(width, width)
            self.ui.thumbnailButton.setIconSize(size)
            self.ui.thumbnailButton.setMaximumSize(size)
            self.ui.thumbnailFrame.setMaximumSize(size)

    def updateContains(self):
        """
        Triggered when the users selection has changed.

        :rtype: None
        """
        if hasattr(self.ui, "contains"):
            count = self.objectCount()
            plural = "s" if count > 1 else ""
            self.ui.contains.setText(str(count) + " Object" + plural)

    def objectCount(self):
        """
        Return the number of selected objects in the Maya scene.

        :rtype: int
        """
        selection = []

        try:
            selection = maya.cmds.ls(selection=True) or []
        except NameError as error:
            logger.exception(error)

        return len(selection)

    def name(self):
        """
        Return the str from the name field.

        :rtype: str
        """
        return self.ui.name.text().strip()

    def description(self):
        """
         Return the str from the comment field.

        :rtype: str
        """
        return self.ui.comment.toPlainText().strip()

    def folderFrame(self):
        """
        Return the frame that contains the folder edit, label and button.

        :rtype: QtWidgets.QFrame
        """
        return self.ui.folderFrame

    def setFolderPath(self, path):
        """
        Set the destination folder path.

        :type path: str
        :rtype: None
        """
        self.ui.folderEdit.setText(path)

    def folderPath(self):
        """
        Return the folder path.

        :rtype: str
        """
        return self.ui.folderEdit.text()

    def browseFolder(self):
        """
        Show the file dialog for choosing the folder location to save the item.

        :rtype: None
        """
        path = self.folderPath()
        path = QtWidgets.QFileDialog.getExistingDirectory(None, "Browse Folder", path)
        if path:
            self.setFolderPath(path)

    def selectionChanged(self):
        """
        Triggered when the Maya selection changes.

        :rtype: None
        """
        self.updateContains()

        if self._optionsWidget:
            self._optionsWidget.validate()

    def _thumbnailCaptured(self, path):
        """
        Triggered when the user captures a thumbnail/playblast.

        :type path: str
        :rtype: None
        """
        self.setIconPath(path)

    def thumbnailCapture(self):
        """
        Capture a playblast and save it to the temp thumbnail path.

        :rtype: None
        """
        path = mutils.gui.tempThumbnailPath()
        mutils.gui.thumbnailCapture(path=path, captured=self._thumbnailCaptured)

    def setCaptureMenuEnabled(self, enable):
        """
        Enable the capture menu for creating the thumbnail.

        :type enable: bool
        :rtype: None 
        """
        logger.info("Setting capture menu to %s", enable)

        if enable:
            parent = self.parent()
            iconPath = mutils.gui.tempThumbnailPath()

            menu = mutils.gui.ThumbnailCaptureMenu(
                iconPath,
                force=True,
                parent=parent
            )
            menu.captured.connect(self._thumbnailCaptured)

            self.ui.thumbnailButton.setMenu(menu)
        else:
            self.ui.thumbnailButton.setMenu(QtWidgets.QMenu(self))

    def showThumbnailCaptureDialog(self):
        """
        Ask the user if they would like to capture a thumbnail.

        :rtype: int
        """
        title = "Create a thumbnail"
        text = "Would you like to capture a thumbnail?"

        buttons = QtWidgets.QMessageBox.Yes | \
                  QtWidgets.QMessageBox.Ignore | \
                  QtWidgets.QMessageBox.Cancel

        parent = self.item().libraryWindow()
        button = studiolibrary.widgets.MessageBox.question(
            parent,
            title,
            text,
            buttons=buttons
        )

        if button == QtWidgets.QMessageBox.Yes:
            self.thumbnailCapture()

        return button

    def accept(self):
        """Triggered when the user clicks the save button."""
        try:
            name = self.name()
            path = self.folderPath()

            objects = maya.cmds.ls(selection=True) or []

            if not path:
                raise Exception("No folder selected. Please select a destination folder.")

            if not name:
                raise Exception("No name specified. Please set a name before saving.")

            if not objects:
                raise Exception("No objects selected. Please select at least one object.")

            if not os.path.exists(self.iconPath()):
                button = self.showThumbnailCaptureDialog()
                if button == QtWidgets.QMessageBox.Cancel:
                    return

            path += "/" + name

            iconPath = self.iconPath()
            metadata = {"description": self.description()}

            self.save(
                objects,
                path=path,
                iconPath=iconPath,
                metadata=metadata,
            )

        except Exception as e:
            title = "Error while saving"
            studiolibrary.widgets.MessageBox.critical(self.libraryWindow(), title, str(e))
            raise

    def save(self, objects, path, iconPath, metadata):
        """
        Save the item with the given objects to the given disc location path.

        :type objects: list[str]
        :type path: str
        :type iconPath: str
        :type metadata: None or dict

        :rtype: None
        """
        item = self.item()
        item.save(
            objects,
            path=path,
            iconPath=iconPath,
            metadata=metadata,
        )
        self.close()
