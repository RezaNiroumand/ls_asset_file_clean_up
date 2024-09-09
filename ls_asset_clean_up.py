import maya.app.renderSetup.model.renderLayer as renderLayer_rs
import maya.app.renderSetup.model.renderSetup as renderSetup_rs
import maya.app.renderSetup.model.collection as collTool

from PySide2 import QtCore, QtUiTools, QtWidgets, QtGui
from PySide2.QtGui import QTextCharFormat, QColor
from maya import OpenMayaUI as omu
from shiboken2 import wrapInstance
import maya.cmds as cmds
import os, shutil, re, sys
import datetime
from functools import partial
import pymel.core as pm
# import getpass
import maya.mel as mel
from contextlib import closing
import sqlite3 as sqlite
import json
import gc
import textwrap
import socket

SCRIPT_FILE_PATH = 'D:/reza_niroumand/Script/ls_asset_file_clean_up/ui/'

mainObject = omu.MQtUtil.mainWindow()
mayaMainWind = wrapInstance(int(mainObject), QtWidgets.QWidget)


class AssetFileClean(QtWidgets.QWidget):    
    
    def __init__(self,parent=mayaMainWind):
        
        super(AssetFileClean, self).__init__(parent=parent)
                   
        if(__name__ == '__main__'):
            self.ui = SCRIPT_FILE_PATH+"ls_asset_file_clean_up.ui"
        else:
            self.ui = os.path.abspath(os.path.dirname(__file__)+'/ui/ls_asset_file_clean_up.ui')
            print(self.ui)
        
        self.setAcceptDrops(True)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle('LS Asset File Clean Up')
        self.resize(800,525)                
        loader = QtUiTools.QUiLoader()
        ui_file = QtCore.QFile(self.ui)
        ui_file.open(QtCore.QFile.ReadOnly)
        self.theMainWidget = loader.load(ui_file)
        ui_file.close()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.theMainWidget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        self.DirtyTemplateCleanup_checkBox = self.findChild(QtWidgets.QCheckBox, "DirtyTemplateCleanup_checkBox")
        self.DeleteLegacyRenderLayers_checkBox = self.findChild(QtWidgets.QCheckBox, "DeleteLegacyRenderLayers_checkBox")
        self.RemoveDataStructure_checkBox = self.findChild(QtWidgets.QCheckBox, "RemoveDataStructure_checkBox")
        self.RemoveUnnecessaryPlugins_checkBox = self.findChild(QtWidgets.QCheckBox, "RemoveUnnecessaryPlugins_checkBox")       
        self.DeleteUnusedRenderSetup_checkBox = self.findChild(QtWidgets.QCheckBox, "DeleteUnusedRenderSetup_checkBox")
        self.DeleteBrokenReferenceNodes_checkBox = self.findChild(QtWidgets.QCheckBox, "DeleteBrokenReferenceNodes_checkBox")

        self.cleanup_pushButton = self.findChild(QtWidgets.QPushButton, "cleanup_pushButton")
        self.cleanup_pushButton.clicked.connect(self.clean_up)
        
        self.log_textEdit = self.findChild(QtWidgets.QTextEdit, "log_textEdit")
        self.log_cursor = self.log_textEdit.textCursor()

    def clean_up(self):
        if (not self.DirtyTemplateCleanup_checkBox.isChecked() and 
            not self.DeleteLegacyRenderLayers_checkBox.isChecked() and
            not self.RemoveDataStructure_checkBox.isChecked() and
            not self.RemoveUnnecessaryPlugins_checkBox.isChecked() and
            not self.DeleteUnusedRenderSetup_checkBox.isChecked() and
            not self.DeleteBrokenReferenceNodes_checkBox.isChecked()):
            cmds.confirmDialog(title=" Warning ", message="Please Select One!")
            return

        self.log_cursor.insertText("Cleanup Starts...")
        if self.DirtyTemplateCleanup_checkBox.isChecked():
            self.log_cursor.insertText("\nDirty Template Cleanup Starts...\n")
            self.dirtyTemplateCleanup()
        
        if self.DeleteLegacyRenderLayers_checkBox.isChecked():
            self.log_cursor.insertText("\nDelete Legacy Render Layers Starts...\n")
            self.DeleteLegacyRenderLayers()
        
        if self.RemoveDataStructure_checkBox.isChecked():
            self.log_cursor.insertText("\nRemove Data Structure Starts...\n")
            self.cleanUpDataStructure()
        
        if self.RemoveUnnecessaryPlugins_checkBox.isChecked():
            self.log_cursor.insertText("\nRemove Unnecessary Plugins Starts...\n")
            self.removeUnknowPlugins()
        
        if self.DeleteUnusedRenderSetup_checkBox.isChecked():
            self.log_cursor.insertText("\nDelete Unused Render Setup Starts...\n")
            self.clean_unsed_render_node()
                
        if self.DeleteBrokenReferenceNodes_checkBox.isChecked():
            self.log_cursor.insertText("\nDelete Broken Reference Nodes Starts...\n")             
            self.lsDeleteBrokenRefNodes()

        cmds.confirmDialog(title=" Clean Up ", message="Clean Up Done. Please Save the File!")
    
    
    
    def lsPlural(self, sum, singular="", plural="s", *args):
        output = []
        
        if isinstance(sum, list):
            sum = len(sum)
        
        output.append(sum)
        if sum == 1:
            if isinstance(singular, list):
                output.extend(singular)
            else:
                output.append(singular)
        else:
            if isinstance(plural, list):
                output.extend(plural)
            else:
                output.append(plural)
                
        if args:
            output.extend(args)

        return output
        
    
    
    
    def lsGetColor(self,color=None):
        if isinstance(color, tuple) or color == None:
            return color
            
        bgcSwitcher = {
                        "red"    : (0.3,0,0),
                        "green"  : (0,0.3,0),
                        "blue"   : (0,0,0.3),
                        "brown"  : (0.3,0.2,0),
                        "purple" : (0.2,0,0.2),
                        "teal"   : (0,0.2,0.2),
                        "darkgrey": (0.25,0.25,0.25),
                    }
        
        return bgcSwitcher.get(color, None)

    def lsDialog(self,**kwargs):
        button=[] #b
        defaultButton=None #db
        cancelButton=None #cb
        dismissString=None #ds
        bgc=None
        icon=None
        
        getInput=False
        dialogMode=kwargs.get("dialog", True)

        dialogKwargs = {}
        
        for k, v in list(kwargs.items()):
            if k=="t" or k=="title": 
                dialogKwargs["title"]=v
            elif k=="m" or k=="message": 
                dialogKwargs["message"]=v
            elif k=="b" or k=="button":
                dialogKwargs["button"] = v
                button = v
            elif k=="db" or k=="defaultButton":
                defaultButton = v
            elif k=="cb" or k=="cancelButton":
                cancelButton = v
            elif k=="ds" or k=="dismissString":
                dismissString = v
            elif k=="icn" or k=="icon":
                icon=v
                dialogKwargs[k] = v
            elif k=="bgc" or k=="backgroundColor":
                bgc = v
            elif k=="getInput":
                getInput = v
            else:
                dialogKwargs[k] = v
        
        if not getInput:
            if "checkbox" in list(kwargs.keys()) or "combobox" in list(kwargs.keys()):
                getInput = True
            
        if bgc:
            bgc = self.lsGetColor(bgc)
            dialogKwargs["backgroundColor"] = bgc
            
        checkButtonValue = [a.lower() for a in button]
        if len(button) > 1:
            dialogKwargs["defaultButton"] = button[0] if defaultButton==None else defaultButton
            dialogKwargs["cancelButton"] = button[len(button)-1] if cancelButton==None else cancelButton
            dialogKwargs["dismissString"] = button[len(button)-1] if dismissString==None else dismissString
        elif len(button) == 1:
            dialogKwargs["defaultButton"] = button[0] if defaultButton==None else defaultButton
            dialogKwargs["cancelButton"] = button[0] if cancelButton==None else cancelButton
            dialogKwargs["dismissString"] = button[0] if dismissString==None else dismissString
        

        while cmds.waitCursor( query=True, state=True ):
            cmds.waitCursor( state=False )
        
        if getInput:
            if "text" not in list(kwargs.keys()):
                dialogKwargs["text"] = False
            dialog = inputDialog(dialog=dialogMode)
            answer = dialog.run(**dialogKwargs)
            return answer
        
        answer = cmds.confirmDialog(**dialogKwargs)
        return answer
            
    
    
    def dirtyTemplateCleanup(self=None):
        global lsOutputMode, lsOutput

        self.log_cursor.insertText("\n"+"\n\n\n" + "_"*75 + "\n\n")

        lsOutputMode = True
        lsOutput = ""

        allError = 0
        allChanges = 0
        error = 0
        sceneChange = 0

        self.log_cursor.insertText("\n"+"Deleting meta nodes...")

        meta_network_nodes = []
        all_objects = cmds.ls(long=True)  # Get all objects with full path names
        for obj in all_objects:
            if cmds.nodeType(obj) == "network" and ("Meta" in obj):
                meta_network_nodes.append(obj)        
               
        
        
        ref_nodes = []
        for node in meta_network_nodes:
            if ':' in node:
                ref_nodes.append(cmds.referenceQuery(node, filename=True).split("{")[0])
            else:
                cmds.delete(node)
                self.log_cursor.insertText("\n"+"[  OK  ]  Deleted '{}'".format(node))
                sceneChange+=1

        if ref_nodes:
            ref_nodes = list(set(ref_nodes))
            for item in ref_nodes:
                cursor = self.log_textEdit.textCursor()
                format = QTextCharFormat()
                format.setForeground(QColor("red"))
                cursor.insertHtml("<br><font color='red'>"+"cannot delete metadata referenced nodes from this file :"+item+"</font><br>")      
        
        if not sceneChange and not error:
            self.log_cursor.insertText("\n"+"[  OK  ]  No meta nodes found")

        allError += error
        allChanges += sceneChange
        error = 0
        sceneChange = 0

        self.log_cursor.insertText("\n"+"Deleting Unknown Vray nodes...")

        unknown_nodes = cmds.ls(type="unknown", long=True)
        all_vrayNodes = [node for node in unknown_nodes if "VRay" or "vray" in cmds.ls(node, long=True)[0]]
        ref_nodes = []
        for node in all_vrayNodes:
            if ':' in node:
                ref_nodes.append(cmds.referenceQuery(node, filename=True).split("{")[0])
            else:
                cmds.delete(node)
                self.log_cursor.insertText("\n"+"[  OK  ]  Deleted '{}'".format(node))
                sceneChange+=1

        if ref_nodes:
            ref_nodes = list(set(ref_nodes))
            for item in ref_nodes:
                cursor = self.log_textEdit.textCursor()
                format = QTextCharFormat()
                format.setForeground(QColor("red"))
                cursor.insertHtml("<br><font color='red'>"+"cannot delete unknown vray referenced nodes from this file :"+item+"</font><br>")


        allError += error
        allChanges += sceneChange
        error = 0
        sceneChange = 0
        notesToDelete = ['''DW 2018-01-10 Pooneh Nasrollahnia
    - created default Section hierarchy and control for Maya 2018. Please note since vray is not yet installed, none of the vrayDisplacement connections are completed. Deleted light display setup as requested
    DW 2018-05-16 Pooneh Nasrollahnia
    - added default vrayDisplacement to the Transform_Ctrl and connected to GeoSmooth attr
    DW 2018-05-16 Pooneh Nasrollahnia
    - Set Geometry Generation in Subdivision and Displacement control to "On the fly" as is new proper settings. This is on the vrayDisplacement
    DW 08/02/2018 Steve Tarin
    - Added a "Misc" Group''', '''Please enter work and approval notes here :-)
    i.e.
    10-22-2013 Artist? Modeler Env. DWTV/DTX
    - Model notes addressed
    - File Submitted for Approval Notes
    10-22-2013 Steve Tarin Lead Env. DWTV/DTX
    --= Model Approved =--
    - Excellent work!
    - Model has been slightly adjusted
    - Please proceed to UVs
    -------------------------------------------------
    DW 1.13.2015 Bill Ballout
    Update.
    -Pivots attrs locked on all ctrls.
    05/06/2016 Clayton Lantz DW
    -Added control for the offset node.
    01-20-2017 Zhuo Huang DW
    - added pivotCtrl for transform ctrl
    08-14-2018 Emmanuel Marenco
    - added Misc group in the main heirarchy.
    01-31-2020 Victor J Garza
    - added default Hair_Growth_Geo_Grp to Hair Grp
    - added default Hair_Def_Grp to Deformers Grp
    2020-04-07 Pooneh Nasrollahnia
    - copied from FFS directory into NDR directory and saved as a Maya 2020 asset''', '''DW 2018-01-09 Pooneh Nasrollahnia
    - created default Set hierarchy and control for Maya 2018.
    DW 2018/06/04 Bobby Clayton
    - Added the XGen group to the default hiearchy.
    DW 08/02/2018 Steve Tarin
    Added "Misc" Group
    Added "Lighting" Group
    Removed Light Indicators
    DW 09/03/2019 Jackie Marion
    Added SC_Set and HR_Set selection sets''']
        notesToDelete = [re.sub("[\n\s]+", "", x) for x in notesToDelete]
        self.log_cursor.insertText("\n"+"Deleting unused notes and Meta attributes...")
        startupCam = cmds.listRelatives([c for c in cmds.ls(type="camera") if cmds.camera(c, q=True, sc=True)], ap=True, ad=False)
        if not startupCam:
            startupCam = []
        attrList = ["notes", "MetaAsset", "MetaSuperSetAsset_link"]
        for n in [n for n in cmds.ls(assemblies=True) if n not in startupCam]:
            for a in attrList:
                if cmds.attributeQuery(a, n=n, ex=True):
                    if a == "notes":
                        v = cmds.getAttr("{}.{}".format(n, a))
                        if v.replace(" ","").replace("\n",""):
                            v = re.sub("\n+", "\n", v)
                            if re.sub("[\n\s]+", "", v) not in notesToDelete:
                                vPreview = v
                                if len(v.splitlines()) > 30:
                                    vPreview = "\n".join(v.splitlines()[:15]) + "\n..."
                                if self.lsDialog(t="Delete notes?", icn="warning", m="{}.{} has notes.\n\n{}\n\n Do you want to clear and delete them?".format(n, a, vPreview), b=["Delete notes", "Keep notes"]) == "Keep notes":
                                    # skip this if the user want to keep
                                    self.log_cursor.insertText("\n"+"Will not delete attribute '{}.{}'! It has value:".format(n, a))
                                    self.log_cursor.insertText("\n"+v, "\n\n")
                                    error+=1
                                    continue
                    try:
                        cmds.deleteAttr("{}.{}".format(n, a))
                    except:
                        self.log_cursor.insertText("\n"+"Could not delete attribute '{}.{}'".format(n, a))
                        error+=1
                    else:
                        self.log_cursor.insertText("\n"+"[  OK  ]  Deleted attribute '{}.{}'".format(n, a))
                        sceneChange+=1
        if not sceneChange and not error:
            self.log_cursor.insertText("\n"+"[  OK  ]  No unused attributes found.")

        allError += error
        allChanges += sceneChange
        error = 0
        sceneChange = 0

        self.log_cursor.insertText("\n"+"Deleting SuperSet_LocGrp...")
        ssLocGrp = cmds.ls("SuperSet_LocGrp", type="transform")
        if ssLocGrp:
            if cmds.listRelatives(ssLocGrp, ad=True, ap=False):
                self.log_cursor.insertText("\n"+"The SuperSet_LocGrp has child objects! Will not delete it to preserve the child objects.")
            else:
                for n in ssLocGrp:
                    try:
                        cmds.delete(n)
                    except:
                        self.log_cursor.insertText("\n"+"Could not delete SuperSet_LocGrp '{}'!".format(n))
                        error+=1
                    else:
                        self.log_cursor.insertText("\n"+"[  OK  ]  Deleted SuperSet_LocGrp '{}'".format(n))
                        sceneChange+=1
        if not sceneChange and not error:
            self.log_cursor.insertText("\n"+"[  OK  ]  No SuperSet_LocGrp found.")

        allError += error
        allChanges += sceneChange
        error = 0
        sceneChange = 0


        if cmds.fileInfo('vrayBuild', q=True):
            self.log_cursor.insertText("\n"+"Removing vrayBuild fileInfo...")
            try:
                cmds.fileInfo(rm='vrayBuild')
            except:
                self.log_cursor.insertText("\n"+"Could not remove vrayBuild fileInfo!")
                error+=1
            else:
                self.log_cursor.insertText("\n"+"[  OK  ]  vrayBuild fileInfo removed.")
                sceneChange+=1

        if cmds.currentUnit(q=True, time=True) != "film":
            self.log_cursor.insertText("\n"+"Setting FPS to 24 fps (film)...")
            try:
                cmds.currentUnit(time="film")
            except:
                self.log_cursor.insertText("\n"+"Setting FPS to 'film' failed!")
                error+=1
            else:
                self.log_cursor.insertText("\n"+"[  OK  ]  FPS set to 'film'.")
                sceneChange+=1

            curTime = cmds.currentTime(q=True)
            if curTime != int(curTime):
                cmds.currentTime(int(curTime), e=True)

            attrList = ["min", "max", "ast", "aet"]
            for a in attrList:
                kwarg = {a: True}
                v = cmds.playbackOptions(query=True, **kwarg)
                if v != int(v):
                    kwarg = {a: int(v)}
                    cmds.playbackOptions(e=True, **kwarg)

        allError += error
        allChanges += sceneChange
        error = allError
        sceneChange = allChanges

        lsOutputMode = False




        if error or sceneChange:
            jRawOutput = lsOutput
            lsOutput = ['<span style="color:yellow;"><b># Warning: </b> {}</span>'.format(line.split("# Warning: ", 1)[-1]) if "# Warning: " in line else line for line in lsOutput.splitlines()]
            lsOutput = ['<br><br><span style="font-size:10pt;font-weight:bold;">{}</span>'.format(line) if line.startswith(">>") else line for line in lsOutput]
            lsOutput = [line.replace("[  OK  ]", '<span style="color:lime;"><b>[  OK  ]</b></span>') if line.startswith("[  OK  ]") else line for line in lsOutput]

            if lsOutput and lsOutput[0].startswith("<br><br>"):
                lsOutput[0] = lsOutput[0][8:]
            resultMsg = "File cleanup done. ({} change{})".format(*self.lsPlural(sceneChange))
  
            if error:
                resultMsg = "{} error{} occured during the cleanup!".format(*self.lsPlural(error))
                jRawOutput = jRawOutput.replace(">>", "\n>>")[1:]



            # lsOutput = ['<span style="font-size:10pt;font-weight:bold;color:{}">{}</span><pre>'.format("yellow" if error else "lime", resultMsg) + "_"*75 + "</pre>"] + lsOutput

            # outputText = "<br>".join(lsOutput)
            # while outputText.startswith("<br>"):
            #     outputText = outputText[4:]
            # lsOutput = ""
            # self.log_cursor.insertText("\n" + resultMsg)
            # self.log_cursor.insertText("\n"+outputText, "Dirty Template Cleanup", 900, 600, rich=True)

            if error:
                self.log_cursor.insertText("\n"+resultMsg)
            else:
                self.log_cursor.insertText("\n"+resultMsg)

        else:
            self.log_cursor.insertText("\n"+"No changes made to the scene. Cleanup is not needed, all looking good.")




    def lsDeleteNodes(self, all=[], getResult=False, objName="node", force=False):
        x=0
        y=0
        
        if all:
            for each in all :
                if not cmds.referenceQuery(each, isNodeReferenced=True):
                    try:
                        if force:
                            cmds.lockNode(each, lock=False)
                        cmds.delete(each)
                    except:
                        y +=1
                        self.log_cursor.insertText("\n"+"Failed to delete: {}".format(each))
                    else:
                        x +=1
                        self.log_cursor.insertText("\n"+"Deleted: {}".format(each))
                else:
                    y +=1
                    self.log_cursor.insertText("\n"+"Failed to delete referenced node: {}".format(each))
        
        if getResult:
            return x, y
            

        
        if y==0:
            if x==0:
                tmpmsg = "No {}s in the scene.".format(objName)
            else:
                tmpmsg = "Deleted {1} {0}{2}.".format(objName, *self.lsPlural(x))
            
            self.log_cursor.insertText("\n"+tmpmsg)
        else:
            if x==0:
                errorMsg = "Failed to delete {1} {0}{2}.".format(objName, *self.lsPlural(y))
            else:
                errorMsg = "Deleted {1} {0}{2}".format(objName, *self.lsPlural(x)) + " and failed to delete {1} {0}{2}.".format(objName, *self.lsPlural(y))
                
            if not force:
                answer = self.lsDialog(t="Try unlock and delete?", icon="warning", m="{}\n\nDo you want to try unlocking and delete?".format(errorMsg), b=["Yes","Cancel"])
                if answer == "Yes":
                    self.lsDeleteNodes(all, False, objName, True)
                    return
            
            self.log_cursor.insertText("\n"+"{}\nConsider clean up from referenced file.".format(errorMsg), True)





    def DeleteLegacyRenderLayers(self):

        self.log_cursor.insertText("\n"+"Deleting Legacy Render Layers...")
        
        render_layers = cmds.listConnections("renderLayerManager.renderLayerId")
        if "defaultRenderLayer" in render_layers:
            render_layers.remove("defaultRenderLayer")
        
        nodes = cmds.ls(type="renderLayer")
        # nodes = [n for n in nodes if n not in ["defaultRenderLayer"]+render_layers]
        nodes = [n for n in nodes if "defaultRenderLayer" not in n if not n.startswith('rs_')]
        
        x, y = 0, 0
        if nodes:
            x, y = self.lsDeleteNodes(nodes, getResult=True)


        
        if y==0:
            if x==0:
                tmpmsg = "No legacy render layers in the scene."
            else:
                tmpmsg = "Deleted {} legacy render layer{}.".format(*self.lsPlural(x))
            
            if render_layers:
                tmpmsg += "\nBut Render Layers found in the scene, please delete them if this is asset file:\n"+"\n".join(render_layers)
                self.log_cursor.insertText("\n"+tmpmsg)
                return
                
            self.log_cursor.insertText("\n"+tmpmsg)
        else:
            if x==0:
                self.log_cursor.insertText("\n"+"Failed to delete {} legacy render layer{}.\nConsider clean up from referenced file.".format(*self.lsPlural(y)), True)
            else:
                self.log_cursor.insertText("\n"+"Deleted {} legacy render layer{}".format(*self.lsPlural(x)) + " and failed to delete {} legacy render layer{}.\nConsider clean up from referenced file.".format(*self.lsPlural(y)), True)

    
    def lsRemoveUnknownPlugins(self):
        
        self.log_cursor.insertText("\n"+"Removing Unknown Required Plugins...")
        
        all = cmds.unknownPlugin(query=True, list=True)
        x = 0
        y = 0

        if all:
            for each in all:
                try:
                    cmds.unknownPlugin(each, remove=True)
                except:
                    y +=1
                    self.log_cursor.insertText("\n"+"Failed to remove: {}".format(each))
                else:
                    x +=1
                    self.log_cursor.insertText("\n"+"Removed: {}".format(each))
        
        if y==0:
            if x==0:
                self.log_cursor.insertText("\n"+"No unknown required plugins in the scene.")
            else:
                self.log_cursor.insertText("\n"+"Removed {} unknown plugin{}.".format(*self.lsPlural(x)))
        else:
            if x==0:
                self.log_cursor.insertText("\n"+"Failed to remove {} unknown plugin{}.\nConsider deleting unknown nodes first.".format(*self.lsPlural(y)), True)
            else:
                self.log_cursor.insertText("\n"+"Removed {} unknown plugin{}".format(*self.lsPlural(x)) + " and failed to remove {} unknown plugin{}.\nConsider deleting unknown nodes first.".format(*self.lsPlural(y)), True)
            
  
    def removeUnsedShader(self):
        pm.mel.MLdeleteUnused()   


    
    
    def removeUnknowPlugins(self):
        #try:
            #cmds.unloadPlugin("Turtle")
            #print("[INFO] Unloaded Turtle Plugins" )
        #except:
            #pass

        unknown_plugin_nodes = cmds.ls(type="unknown")
        for unknown_nodes in unknown_plugin_nodes:
            if unknown_nodes == "vraySettings":
                cmds.delete(unknown_nodes)
                print("-----------------------------------------------------")
                print("[INFO] delete "+ str(unknown_plugin_nodes))
                cmds.confirmDialog(t="unknow node found",m="removed "+str(unknown_nodes))
        self.lsRemoveUnknownPlugins()
        return unknown_plugin_nodes


    def removenNodeGraph(self):
        nodeGraph = cmds.ls(type="nodeGraphEditorInfo")
        ref_nodes = []
        for node in nodeGraph:
            if "hyperShadePrimaryNodeEditorSavedTabsInfo" in node:
                pass
            else:
                if ':' in node:
                    # extract undeletable ref npodes)
                    ref_nodes.append(cmds.referenceQuery(node, filename=True).split("{")[0])
                else:
                    cmds.delete(node)
        if ref_nodes:
            ref_nodes = list(set(ref_nodes))
            for item in ref_nodes:
                cursor = self.log_textEdit.textCursor()
                format = QTextCharFormat()
                format.setForeground(QColor("red"))
                cursor.insertHtml("<font color='red'>"+"cannot delete unused referenced nodes from this file :"+item+"</font><br>")




                




    def cleanUpDataStructure(self):
        self.removeUnsedShader()
        self.removenNodeGraph()
        dataStructure = cmds.dataStructure(query=True)
        if dataStructure:
            for data in dataStructure:
                cmds.dataStructure(remove=True, name=data)
                print("Deleted = " + data)





    def lsReplaceAll(self, input, search=[], replaceWith="", removeLeadingSlash=False, ignoreCase=True, escapeString=True):
        if not isinstance(search, list):
            search = [search]
        
        p = input
        
        for eachSearch in search:
            if isinstance(eachSearch, type(re.compile('foo'))):
                pattern = eachSearch
            else:
                if escapeString:
                    pattern = re.escape(eachSearch)
                else:
                    pattern = eachSearch
                    
                if ignoreCase:
                    pattern = re.compile(pattern, re.I | re.M)
                else:
                    pattern = re.compile(pattern, re.M)
            
            p = re.sub(pattern, replaceWith, p)
        
        while removeLeadingSlash and p.startswith(("/","\\")):
            p = p[1:]
            
        return p

    def lsPathJoin(self, *args, **kwargs):
        useBackslash = False
        removeEndingSlash = False
        for key, value in list(kwargs.items()):
            if key == "backslash" or key == "bs":
                useBackslash = value
            if key == "removeEndingSlash" or key == "res":
                removeEndingSlash = value
                
        newPath = os.path.join(*args).replace("\\","/")
        if newPath.startswith("//"):
            newPath = "//" + self.lsReplaceAll(newPath[2:], re.compile("\/+", re.M), "/")
        else:
            newPath = self.lsReplaceAll(newPath, re.compile("\/+", re.M), "/")
        
        if removeEndingSlash:
            while newPath.endswith("/"):
                newPath = newPath[:-1]
        
        if useBackslash:
            return newPath.replace("/","\\")
        return newPath



    def lsCache(self, method="get", db=None, file=None, data=None):
        # accepted method: get, post
        if file is None or db is None or method not in ["get", "post"]:
            return
        
        if method == "post" and data is None:
            return
        
        result = None
        
        d = os.path.dirname(db)
        if not os.path.isdir(d):
            os.makedirs(d)
        
        try:
            with closing(sqlite.connect(db)) as sql_conn:
                with closing(sql_conn.cursor()) as c:
                    
                    # create the table if it does not exist yet
                    c.execute("CREATE TABLE IF NOT EXISTS cache (id INTEGER PRIMARY KEY AUTOINCREMENT, file TEXT, data LONGTEXT)")
                    
                    result = c.execute("SELECT id, file, data FROM cache WHERE LOWER(file) = ?;", (file.lower(), )).fetchall()
                    
                    to_commit = False
                    
                    if result:
                        if len(result) > 1:
                            for row in result[:-1]:
                                c.execute("DELETE FROM cache WHERE id = ?;", (row[0], ))
                                to_commit = True
                    else:
                        result = None
                    
                    if method == "post":
                        if result:
                            c.execute("UPDATE cache SET data = ? WHERE LOWER(file) = ?;", (data, file.lower()))
                        else:
                            c.execute("INSERT INTO cache(file,data) VALUES (?, ?);", (file, data))
                        to_commit = True
                    
                    if result:
                        # retrieving data of the last row
                        result = result[-1][-1]
                    
                    if to_commit:
                        sql_conn.commit()
        except:
            return

        return result



    def lsProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=25, clear=True, isCancelled=False):

        gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')
        
        if not cmds.progressBar(gMainProgressBar, query=True, visible=True ):
            cmds.progressBar( gMainProgressBar,
                            edit=True,
                            beginProgress=True,
                            isInterruptable=False,
                            status=' '.join([prefix, suffix]),
                            maxValue=total )

        if isCancelled:
            if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True ) :
                cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
                return True
            else:
                return False

        cmds.progressBar(gMainProgressBar, edit=True, progress=iteration)
        
        if iteration >= total:
            cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

        






    def lsReadFile(self, fp=None, checkThisFile=False, find="reference", rescan=False, cache=None):
        
        whitelistPlugin = ["stereoCamera","Turtle","renderSetup.py","MASH","mtoa","matrixNodes", "Type", "lookdevKit",
                                                                "AbcImport", "ikSpringSolver", "AbcBullet","AbcExport","AbcImport","animImportExport","ArubaTessellator","atomImportExport",
                                                                "AutodeskPacketFile","autoLoader","bullet","cacheEvaluator","cgfxShader","cleanPerFaceAssignment","clearcoat","curveWarp",
                                                                "ddsFloatReader","deformerEvaluator","dgProfiler","dx11Shader","fltTranslator","freeze","Fur","gameFbxExporter","GamePipeline",
                                                                "glslShader","GPUBuiltInDeformer","gpuCache","hairPhysicalShader","Iges","ik2Bsolver","ikSpringSolver","image","lookdevKit",
                                                                "matrixNodes","mayaCharacterization","mayaHIK","MayaMuscle","melProfiler","meshReorder","modelingToolkit","nearestPointOnMesh",
                                                                "objExport","OneClick","OpenEXRLoader","quatNodes","renderSetup.py","retargeterNodes","rotateHelper","sceneAssembly","shaderFXPlugin",
                                                                "shotCamera","stereoCamera","stlTranslator","studioImport","svgFileTranslator.py","tiffFloatReader","timeSliderBookmark","Turtle",
                                                                "Type","Unfold3D","VectorRender","ATFPlugin","MASH","MayaScanner","fbxmaya","invertShape","poseInterpolator","mtoa","Substance",
                                                                "subtancemaya","subtanceworkflow.py","xgenToolkit","xgSplineDataToXpd"
                                                                ]
        
        patternSwitcher = {
                'reference': r'file -rdi 1(?:[\s]+\-\w+[\s]+(?:\"[^\"]+\"|\d+))*\s*\"([^\"]+)\";',
                'plugin': r'requires(?:(?:\t\t)? (?:-nodeType||-dataType) \"[^\"]+\"\n?)* \"([^\"]+)\"(?: \"[^\"]+\")?;\r?\n',
                'abcFile': r'\s*\"([^\"]+\.abc)\";',
                'assFile': r'\s*\"([^\"]+\.ass)\";',
                'textureFile': r'\s*\"([^\"\:]+\.(?:png|jpeg|jpg|tif|tiff|tga|exr|tx|bmp))\";',
                'infected': '(?:vaccine_gene)|(?:breed_gene)|(?:fuck_All_U|\$PuTianTongQing)'
            }
        
        if checkThisFile and find=="plugin":
            if fp == cmds.file(q=True, sn=True):
                unknownPluginFound = cmds.unknownPlugin(query=True, list=True)
                if unknownPluginFound:
                    unknownPluginFound = [a for a in unknownPluginFound if a not in whitelistPlugin]
                    unknownPluginFound.sort()
                    return unknownPluginFound
                else:
                    return []

        if not fp:
            return None
        
        fp = self.lsPathJoin(fp)
        
        if not os.path.isfile(fp):
            self.log_cursor.insertText("\n"+"File not found: " + fp)
            return None
        
        if not fp.lower().endswith(".ma") and not find in ["infected"]:
            self.log_cursor.insertText("\n"+"Not Maya ASCII file. File not accepted: " + fp)
            return None
        
        if not fp.lower().endswith((".ma",".mb")):
            self.log_cursor.insertText("\n"+"Not Maya file. File not accepted: " + fp)
            return None
        
        if os.stat(fp).st_size == 0:
            self.log_cursor.insertText("\n"+"File is 0 bytes: " + fp)
            return None
        
        if find not in list(patternSwitcher.keys()):
            self.log_cursor.insertText("\n"+"find {} not accepted.".format(find))
            return None
        
        if fp.lower().startswith(("c:","d:","e:","x:")):
            # do not use cache system for local files
            cache = None
        
        now = datetime.datetime.now()
        filesize = os.stat(fp).st_size
        modTime = os.stat(fp).st_mtime
        modTime = datetime.datetime.fromtimestamp(modTime)
        
        json_data = {}
        use_cache = False

        if cache:
            cache_result = self.lsCache(method="get", db=cache, file=fp)
            if cache_result is not None:
                json_data = json.loads(cache_result)
                
                cached_filesize = json_data['_info']['filesize']
                cached_modTime = json_data['_info']['modtime']
                cached_modTime = datetime.datetime.strptime(cached_modTime, '%Y-%m-%d %H:%M:%S.%f')
                
                _data = json_data['data']
                
                if filesize == cached_filesize and modTime == cached_modTime and find in list(json_data['data'].keys()):
                    use_cache = True
        
        if not use_cache:
            rescan = True
            
        if rescan:
            _data = {}
            for each_find in ["reference","plugin"]:
                _data[each_find] = []
                
            fileContent = []
            limit = 2000
            iLine = 0
            capturing = False
            with open(fp, 'r') as fr:
                while True: 
                    iLine+=1
                    if iLine>limit:
                        self.log_cursor.insertText("\n"+"Loop iteration limit exceeded...")
                        break
                        
                    thisLine = fr.readline() 
                    
                    if thisLine.startswith(("createNode ","\trename ","\tsetAttr ")):
                        capturing = False
                        break
                    
                    if thisLine.startswith(("//Maya ASCII ")):
                        capturing = True
                    
                    if iLine > 5 and not capturing:
                        self.log_cursor.insertText("\n"+"This file does not look like Maya file")
                        break
                    
                    if capturing:
                        fileContent.append(thisLine)
                    
            if fileContent:
                if isinstance(fileContent, list):
                    fileContent = "".join(fileContent)
                
                for each_find in ["reference","plugin"]:
                    pattern = re.compile(patternSwitcher[each_find], re.I | re.M)
                    pFound = re.findall(pattern, fileContent)
                    if pFound:
                        pFound = list(dict.fromkeys(pFound))
                        pFound.sort()
                        _data[each_find] = pFound
            
            if find not in ["reference","plugin"]:
                gc.collect()
                
                find_rest = [k for k in list(patternSwitcher.keys()) if k not in ["reference","plugin"]]
                for each_find in find_rest:
                    _data[each_find] = []
                

                fileContent = []
                
                startTime = datetime.datetime.now()
                lastTime = startTime
                
                if filesize > 20000000:

                    self.lsProgressBar(0, filesize, 'Reading... ', fp)                    
                    with open(fp, 'r') as fr:
                        for thisLine in fr:
                            if thisLine.startswith("\t"):
                                fileContent.append(thisLine)
                            else:
                                if fileContent:
                                    if isinstance(fileContent, list):
                                        fileContent = "".join(fileContent)
                                        
                                    for each_find in find_rest:
                                        pattern = re.compile(patternSwitcher[each_find], re.I | re.M)
                                        thisFound = re.findall(pattern, fileContent)
                                        if thisFound:
                                            _data[each_find] += [_tf for _tf in thisFound if "/" in _tf and "\\" in _tf and each_find.endswith("File")]
                                            
                                
                                fileContent = [thisLine]
                        
                            now = datetime.datetime.now()
                            if (now - lastTime).total_seconds() > 0.5:
                                lastTime = now
                                self.lsProgressBar(fr.tell(), filesize)
                                
                        self.lsProgressBar(filesize, filesize)
                else:
                    with open(fp, 'r') as fr:
                        fileContent = fr.read()
                        
                        if fileContent:
                            for each_find in find_rest:
                                pattern = re.compile(patternSwitcher[each_find], re.I | re.M)
                                thisFound = re.findall(pattern, fileContent)
                                if thisFound:
                                    _data[each_find] += thisFound
        
        # cleaning and sort
        for k in list(_data.keys()):
            pFound = _data[k]
            if k.endswith("File"):
                pFound = [_tf for _tf in pFound if "/" in _tf or "\\" in _tf]
            pFound = list(dict.fromkeys(pFound))
            pFound.sort()
            _data[k] = pFound
        
        
        
        if cache and rescan:
            username = os.getenv('username')

            try:
                machinename = socket.gethostname()
            except:
                machinename = "unknown"



            json_data = {}
            json_data['_info'] = {
                    "time": now.strftime("%Y-%m-%d %H:%M:%S"), 
                    "mayaFile": fp, 
                    "username": username.lower(),
                    "machine": machinename.upper(),
                    "filesize": filesize, 
                    "modtime": modTime.strftime("%Y-%m-%d %H:%M:%S.%f")
                }
            
            json_data['data'] = _data

            self.lsCache(method="post", db=cache, file=fp, data=json.dumps(json_data))
        
        
        # pattern = re.compile(pattern, re.I | re.M)
        
        if find in list(_data.keys()):
            if find == "plugin":
                pFound = _data[find]
                return [a for a in pFound if a not in whitelistPlugin]
            return _data[find]



    def lsSummarizeQuickPluginCheck(self,data):
        if not isinstance(data, list):
            data = [data]
        totalIssue = {}
        for each in data:
            if each.get("child"):
                thisChildIssue = self.lsSummarizeQuickPluginCheck(each["child"])
                for k, v in list(thisChildIssue.items()):
                    if totalIssue.get(k):
                        totalIssue[k]+=v
                    else:
                        totalIssue[k]=v
                        
            if each.get("issue"):
                for a in each.get("issue"):
                    if totalIssue.get(a):
                        totalIssue[a]+=1
                    else:
                        totalIssue[a]=1
        return totalIssue







    def lsQuickPluginCheck(self, path=None, level=0, last=[], checkThisFile=None, input=None, quiet=False, checkInfected=True, cache=None):
        plugin_list = ["stereoCamera","Turtle","renderSetup.py","MASH","mtoa","matrixNodes", "Type", "lookdevKit",
                                    "AbcImport", "ikSpringSolver", "AbcBullet","AbcExport","AbcImport","animImportExport","ArubaTessellator","atomImportExport",
                                    "AutodeskPacketFile","autoLoader","bullet","cacheEvaluator","cgfxShader","cleanPerFaceAssignment","clearcoat","curveWarp",
                                    "ddsFloatReader","deformerEvaluator","dgProfiler","dx11Shader","fltTranslator","freeze","Fur","gameFbxExporter","GamePipeline",
                                    "glslShader","GPUBuiltInDeformer","gpuCache","hairPhysicalShader","Iges","ik2Bsolver","ikSpringSolver","image","lookdevKit",
                                    "matrixNodes","mayaCharacterization","mayaHIK","MayaMuscle","melProfiler","meshReorder","modelingToolkit","nearestPointOnMesh",
                                    "objExport","OneClick","OpenEXRLoader","quatNodes","renderSetup.py","retargeterNodes","rotateHelper","sceneAssembly","shaderFXPlugin",
                                    "shotCamera","stereoCamera","stlTranslator","studioImport","svgFileTranslator.py","tiffFloatReader","timeSliderBookmark","Turtle",
                                    "Type","Unfold3D","VectorRender","ATFPlugin","MASH","MayaScanner","fbxmaya","invertShape","poseInterpolator","mtoa","Substance",
                                    "subtancemaya","subtanceworkflow.py","xgenToolkit","xgSplineDataToXpd"
                                    ]
        
        uPipe = "\u2502" 
        uPipeB = "\u251C"  
        uPipeEnd = "\u2514"  
        uDash = "\u2500"  
        uRedCircle = "\U0001F534" 
        uGreenCircle = "\U0001F7E2" 
        uCross = "\u274C" 
        uCheck = "\u2705"  
        uWarning = "\u26A0"        
        

        if input:
            path=input
            indentSpace = " "*5+"\t "
            indentLeft = [(indentSpace+" " if x else indentSpace+uPipe) for x in last]
            indentLeft[0] = " "+uPipe if indentLeft[0].replace(" ","").replace("\t","") else "  "
            indentLeft = "".join(indentLeft)
            try: pipe = uPipeEnd if last[-1] else uPipeB
            except: pipe = uPipeB
            
            relPath = None
            if not os.path.isabs(path):
                relPath = path
                try:
                    projDir = cmds.workspace(query=True, rootDirectory=True)
                except:
                    
                    # projDir = self.lsGetPath("projectDir")
                    projDir = False
                path = self.lsPathJoin(projDir, relPath)
                
            thisOutput = []
            thisRef = {}
            thisRef['path'] = path
            thisRef['issue'] = []
            
            fileExists = os.path.isfile(path)
            isMaFile = path.lower().endswith(".ma")
            
            childRefs = False
            infected = False
            if fileExists:
                if checkThisFile:
                    try: childRefs = cmds.referenceQuery(path,filename=True,child=True,withoutCopyNumber=True)
                    except: childRefs = False
                    if childRefs:
                        childRefs = list(dict.fromkeys(childRefs))
                        childRefs.sort()
                else:
                    if isMaFile:
                        childRefs = self.lsReadFile(path, checkThisFile=checkThisFile, find="reference", cache=cache)
                if checkInfected:
                    infected = self.lsReadFile(path, checkThisFile=checkThisFile, find="infected", cache=cache)
                
            indentChild = indentLeft+indentSpace+uPipe+"\t" if childRefs else indentLeft+indentSpace+" \t"
            thisPathTitle = indentLeft[:-1] + pipe + uDash*5 + "\t{status}\t" + path
            
            pluginFound = False
            if fileExists and isMaFile:
                pluginFound = self.lsReadFile(path, checkThisFile=checkThisFile, find="plugin", cache=cache)
                
            if infected or pluginFound:
                thisOutput.append(thisPathTitle.format(status=uRedCircle))
                
                if infected:
                    thisRef['issue'].append("Infected")
                    thisRef['infected'] = infected
                    thisOutput.append(indentChild + " " + uWarning + " " + "Infected! {} keyword hit{}: ".format(*self.lsPlural(infected)))
                    
                    for a in textwrap.wrap(", ".join(infected), width=80):
                        thisOutput.append(indentChild + " "+ " "*3 + a)
                    thisOutput.append(indentChild)
                    
                if pluginFound:
                    thisRef['issue'].append("Plugin found")
                    thisRef['plugin'] = pluginFound
                    thisOutput.append(indentChild + " " + uWarning + " " + "{} Plugin{} found: ".format(*self.lsPlural(pluginFound)))
                    
                    for a in textwrap.wrap(", ".join(pluginFound), width=80):
                        thisOutput.append(indentChild + " "+ " "*3 + a)
                    thisOutput.append(indentChild)
            elif fileExists:
                if isMaFile:
                    thisOutput.append(thisPathTitle.format(status=uGreenCircle)) 
                else:
                    thisRef['issue'].append("Not Maya ASCII file")
                    thisOutput.append(thisPathTitle.format(status=uCross))
                    thisOutput.append(indentChild + " " + uCross + " Not Maya ASCII file. Could not check the file!")
                    thisOutput.append(indentChild)
            else:
                if relPath:
                    thisRef['issue'].append("Relative path could not be solved")
                    thisOutput.append(thisPathTitle.format(status=uCross))
                    thisOutput.append(indentChild + " " + uCross + " File is using relative path, could not be found!")
                    thisOutput.append(indentChild + "    "+relPath)
                else:
                    thisRef['issue'].append("File not found")
                    thisOutput.append(thisPathTitle.format(status=uCross))
                    thisOutput.append(indentChild + " " + uCross + " File not found!")
                    
                thisOutput.append(indentChild)
            
            if not quiet: self.log_cursor.insertText("\n"+"\n".join(thisOutput))
            
            
            if childRefs:
                thisRef['child'] = []
                i=0
                for a in childRefs:
                    i+=1
                    thisRef['child'].append(self.lsQuickPluginCheck(level=level + 1, last=last + [i == len(childRefs)],
                                                            checkThisFile=checkThisFile, input=a, quiet=quiet,
                                                            checkInfected=checkInfected, cache=cache))
            
            return thisRef
        elif level>0:
            return None
        
        # ----------------
        
        if quiet:
            if not checkThisFile:
                if not path:
                    self.log_cursor.insertText("\n"+"Path missing.")
                    return
                
                if not os.path.isfile(path):
                    self.log_cursor.insertText("\n"+"File not found: " + path)
                    return
            
                if not path.lower().endswith(".ma"):
                    self.log_cursor.insertText("\n"+"Not Maya ASCII file. Could not check the file: " + path)
                    return
        else:
            askInput = True
            if path:
                if os.path.isfile(path) or path.lower().endswith(".ma"):
                    askInput = False
                    
            if checkThisFile in [True, False]:
                askInput = False
            
            if askInput:
                answer = self.lsDialog(t="Check This File?", m="Check Unknown Plugins of this file and referenced file?", b=["This File","Other File","Cancel"])
                if answer == "This File":
                    checkThisFile = True
                elif answer == "Other File":
                    checkThisFile = False
                    
                    localDir = ""
                    
                    filePath = cmds.file(q=True, sn=True)
                    multipleFilters = "Maya ASCII (*.ma)"
                    if os.environ["PROJNAME"]:
                        caption = os.environ["PROJNAME"] + " Open"
                    else:
                        caption = "Open"
                    
                    curDir = self.lsPathJoin(os.getenv('userprofile'), "Desktop")
                    
                    if filePath:
                        curDir = os.path.dirname(filePath)
                    elif localDir:
                        if os.path.isdir(localDir):
                            curDir = localDir
                    
                    path = self.lsFileDialog(fileFilter=multipleFilters, caption=caption, fileMode=1, dir=curDir)
                    
                    if not path:
                        return
                    
                else:
                    self.log_cursor.insertText("\n"+"Canceled.")
                    return
        
        if not quiet:
            self.log_cursor.insertText("\n"+"Checking Unknown Plugins...")
        
        thisOutput = []
        
        if checkThisFile:
            # this function below is using opened file, we're gonna use maya built-in function to get reference info
            
            thisOutput.append("   (This File)")
            
            allRef = cmds.ls(type="reference")
            
            topRefs = []
            for each in allRef:
                try: a = cmds.referenceQuery(each,rfn=True,tr=True)
                except: continue
                if a not in topRefs: topRefs.append(a)
            
            allRef = []
            for each in topRefs:
                isLoaded = False
                resolvedPath = None
                try:
                    isLoaded = cmds.referenceQuery(each, isLoaded=True)
                    resolvedPath = cmds.referenceQuery(each, filename=True, withoutCopyNumber=True)
                except:
                    continue
                
                if isLoaded and resolvedPath not in allRef:
                    allRef.append(resolvedPath)
                    
            allRef = list(dict.fromkeys(allRef))
            allRef.sort()
            
            path = cmds.file(q=True, sn=True)
            
            infected = False
            pluginFound = self.lsReadFile(path, checkThisFile=checkThisFile, find="plugin", cache=cache)
            
            path = path if path else "untitled"
            
        else:
            # this function below to read another file, we're gonna read the ma header file and parse the data
            allRef = self.lsReadFile(path, checkThisFile=checkThisFile, find="reference", cache=cache)
            pluginFound = self.lsReadFile(path, checkThisFile=checkThisFile, find="plugin", cache=cache)
            infected = False
            if checkInfected:
                infected = self.lsReadFile(path, checkThisFile=checkThisFile, find="infected", cache=cache)
        
        toReturn = {}
        toReturn['path'] = path
        toReturn['infected'] = []
        toReturn['plugin'] = []
        toReturn['issue'] = []
        if pluginFound:
            toReturn['plugin'] = pluginFound
        if infected:
            toReturn['infected'] = infected
        toReturn['child'] = []
        
        indentLeft = " "+uPipe if allRef else "  "
        
        if infected or pluginFound:
            thisOutput.append(uRedCircle+"\t"+path)
            
            if infected:
                toReturn['issue'].append("Infected")
                thisOutput.append(indentLeft + "\t" + uWarning + " " + "Infected! {} keyword hit{}: ".format(*self.lsPlural(infected)))
                
                for a in textwrap.wrap(", ".join(infected), width=80):
                    thisOutput.append(indentLeft + "\t"+ " "*3 + a)
                
            if pluginFound:
                toReturn['issue'].append("Plugin found")
                thisOutput.append(indentLeft + "\t" + uWarning + " " + "{} Plugin{} found: ".format(*self.lsPlural(pluginFound)))
                
                for a in textwrap.wrap(", ".join(pluginFound), width=80):
                    thisOutput.append(indentLeft + "\t" + " "*3 + a)
        else:
            thisOutput.append(uGreenCircle+"\t"+path)
        thisOutput.append(indentLeft)
        
        noWhitelistPluginMsg = "No whitelist plugin list provided.\nShowing all required plugins including the one needed for the project.\nThe result shown as it is. Please use with caution!!"
        
        if not quiet: 
            global lsOutput, lsOutputMode
            lsOutputMode = True
            lsOutput = ""
            
            if not plugin_list:
                self.log_cursor.insertText("\n"+uWarning + " WARNING:\n\n" + noWhitelistPluginMsg)
                self.log_cursor.insertText("\n"+"_" * 75 + "\n")
            
            self.log_cursor.insertText("\n"+"\n".join(thisOutput))

        i = 0
        isLast = False
        if allRef:
            for each in allRef:
                i+=1
                if i==len(allRef): isLast=True
                toReturn['child'].append(self.lsQuickPluginCheck(last=[isLast], checkThisFile=checkThisFile, input=each,
                                                            quiet=quiet, checkInfected=checkInfected, cache=cache))
        
        thisSummary = []
        summary = self.lsSummarizeQuickPluginCheck(toReturn)
        
        if not quiet: 
            self.log_cursor.insertText("\n"+"\n" + "_" * 50 + "\n")
            if summary:
                self.log_cursor.insertText("\n"+uWarning + " WARNING!", "\n\n")
                self.log_cursor.insertText("\n"+"\n".join(["- {}: {} file{}".format(k, *self.lsPlural(v)) for k, v in list(summary.items())]), "\n\n\n")
                lsOutputMode = False
                tmpmsg = "  ".join(["{}: {} file{}.".format(k, *self.lsPlural(v)) for k, v in list(summary.items())])
                if not plugin_list:
                    tmpmsg += " \n"+noWhitelistPluginMsg
                self.log_cursor.insertText("\n"+tmpmsg)
            else:
                self.log_cursor.insertText("\n"+uCheck + "  No Unknown Required Plugin found. ")
        
            lsOutputMode = False
            self.log_cursor.insertText("\n"+lsOutput, "RequiredPlugin Check Output")
        
        if not quiet:
            self.log_cursor.insertText("\n")
        return toReturn







    def lsQuickPluginCheckResult(self):
        result = self.lsQuickPluginCheck(checkThisFile=True, quiet=True, checkInfected=False)
        summary = self.lsSummarizeQuickPluginCheck(result)
        if summary:
            self.log_cursor.insertText("\n"+"\n".join(["- {}: {} file{}".format(k, *self.lsPlural(v)) for k, v in list(summary.items())]) + "\n\nConsider checking thoroughly from \nlsTools > Tools > Cleanup > Check Required Plugins.", True)
        else:
            self.log_cursor.insertText("\n"+"No Unknown Required Plugin found.")




    def lsRemoveUnknownPluginsAsset(self):
        self.removeUnknowPlugins()
        self.lsQuickPluginCheckResult()




    def clean_unsed_render_node(self):

        get_used_render_setup = cmds.ls(type="renderSetup")
        ren_layer = cmds.ls(type = 'renderLayer')
        select_aovs = cmds.ls(type="aiAOV")
        select_aovs_filter = cmds.ls(type="aiAOVFilter")

        delete_render_list = [] 

        get_used_render_setup = cmds.ls(type="renderSetup")
        render_setup_layer = cmds.ls(type="renderSetupLayer")
        render_setup = renderSetup_rs.instance()
        if render_setup_layer:
            for layer in render_setup_layer:
                render_layer_s = render_setup.getRenderLayer(layer) 
                collections = render_layer_s.getCollections()
                if collections:
                    for coll  in collections:
                        collTool.delete(coll) 
                renderLayer_rs.delete(render_layer_s)
                self.log_cursor.insertText("\n"+"Done Delete  Render Setup Layers")
        else:
            self.log_cursor.insertText("\n"+"No Unsed Render Setup")

        '''
        if get_used_render_setup:
            cmds.delete(get_used_render_setup)
            self.log_cursor.insertText("\n"+"Done Delete Unsed Render Setup")
        '''
        for ren in ren_layer:
            if 'defaultRenderLayer' in ren:
                continue
            delete_render_list.append(ren)
            cmds.delete(ren)
        
        if delete_render_list:
            self.log_cursor.insertText("\n"+"Done Delete Render Layer {0}".format(delete_render_list))


        if select_aovs:
            cmds.delete(select_aovs)
        if select_aovs_filter:
            cmds.delete(select_aovs_filter)
        




    def lsDeleteBrokenRefNodes(self):
        self.log_cursor.insertText("\n"+"Deleting Broken Reference Nodes...")
        all = cmds.ls(type="reference", r=True)
        excludeList =  cmds.ls("*sharedReferenceNode", r=True)
        for each in excludeList:
            if each in all:
                all.remove(each) #excluding default node
        
        x=0
        newAll = []
        for each in all:
            try:
                cmds.referenceQuery( each, filename=True, unresolvedName=True, withoutCopyNumber=True )
            except:
                newAll.append(each)

        self.lsDeleteNodes(newAll, objName="broken reference node")
        






class inputDialog(QtWidgets.QDialog):
    def __init__(self, dialog=True):
        if dialog:
            QtWidgets.QDialog.__init__(self, [i for i in QtWidgets.QApplication.topLevelWidgets() if i.objectName() == 'MayaWindow'][0])


        else:

            try:
                qw = omu.MQtUtil.findWindow("lsGTools")
                parent = wrapInstance(int(qw), QtWidgets.QWidget)
            except:
                parent = None

            QtWidgets.QDialog.__init__(self, parent)
        
    def run(self, title="", message="", text="", readOnly=False, placeholder="", validate=None, password=False, suggestion=[], suggestionOnCombobox=False, button=["OK", "Cancel"], multiLine=False, vertical=False, comboboxOnTextPosition=None, combobox=[], selectedCombobox=0, checkbox=[], radio=[], selectedRadio=0, order=['text','combobox','checkbox','radio'], defaultButton="OK", cancelButton="Cancel", resize=None, **kwargs):
        if not title:
            title = "MAYA"
        self.setWindowTitle(title)
        self.setMinimumWidth(250)
        
        if resize is not None:
            self.resize(*resize)
        
        self.buttonClicked = None
        self.buttonFocused = 0
        self.order = order
        layout = QtWidgets.QVBoxLayout()
        
        if message:
            qmessage = QtWidgets.QLabel(message, self)
            qmessage.setAlignment(QtCore.Qt.AlignTop)
        
        self.validate = None
        self.completer = None
        self.suggestion = None
        if not text == False:
            if multiLine:
                self.input = QtWidgets.QTextEdit(text, self)
            else:
                self.input = QtWidgets.QLineEdit(text, self)
                if password:
                    self.input.setEchoMode(QtWidgets.QLineEdit.Password)
                if placeholder:
                    self.input.setPlaceholderText(placeholder)
                if suggestion:
                    self.suggestion = suggestion
                    self.completer = QtWidgets.QCompleter(suggestion)
                    self.completer.setFilterMode(QtCore.Qt.MatchContains)
                    self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
                    self.input.setCompleter(self.completer)
                    self.input.mouseReleaseEvent = self.refreshCompleter
                        
                if validate:
                    self.input.textChanged.connect(partial(self.checkState, validate))
                    self.input.textChanged.emit(self.input.text())
            if readOnly:
                self.input.setReadOnly(True)
                    
        self.combobox = None
        if combobox:
            self.combobox = QtWidgets.QComboBox(self)
            self.combobox.setFocusPolicy(QtCore.Qt.StrongFocus)
            for eachCombo in combobox:
                self.combobox.addItem(eachCombo)
            if isinstance(selectedCombobox, str) or isinstance(selectedCombobox, str):
                try: selectedCombobox = combobox.index(selectedCombobox)
                except: selectedCombobox = 0
            if selectedCombobox > len(combobox)-1:
                selectedCombobox = 0
            if self.completer and suggestion and suggestionOnCombobox and comboboxOnTextPosition in ['left', 'right']:
                self.combobox.currentTextChanged.connect(partial(self.updateSuggestion, comboboxOnTextPosition))
            self.combobox.setCurrentIndex(selectedCombobox)
            

        self.checboxList = []
        if checkbox:
            for eachCb in checkbox:
                thisCb = eachCb
                if not isinstance(thisCb, tuple):
                    thisCb = (thisCb, False)
                thisCheckbox = QtWidgets.QCheckBox(thisCb[0], self)
                thisCheckbox.setFocusPolicy(QtCore.Qt.StrongFocus)
                if thisCb[1]:
                    thisCheckbox.setCheckState(QtCore.Qt.CheckState.Checked)
                self.checboxList.append(thisCheckbox)
        
        self.radioList = []
        if radio:
            if isinstance(selectedRadio, int):
                if selectedRadio < len(radio):
                    selectedRadio = radio[selectedRadio]
                else:
                    selectedRadio = radio[0]
            elif selectedRadio not in radio:
                selectedRadio = radio[0]
            for eachRadio in radio:
                thisRb = eachRadio
                if not isinstance(thisRb, tuple):
                    thisRb = (thisRb, True)
                thisRadio = QtWidgets.QRadioButton(thisRb[0], self)
                if thisRb[1]:
                    thisRadio.setFocusPolicy(QtCore.Qt.StrongFocus)
                    if eachRadio == selectedRadio:
                        thisRadio.setChecked(True)
                else:
                    thisRadio.setEnabled(False)
                self.radioList.append(thisRadio)
        
        textInputLayout = None
        if comboboxOnTextPosition in ['left', 'right'] and self.combobox:
            textInputLayout = QtWidgets.QHBoxLayout()
            if comboboxOnTextPosition == 'left':
                textInputLayout.addWidget(self.combobox)
                textInputLayout.addWidget(self.input)
            else:
                textInputLayout.addWidget(self.input)
                textInputLayout.addWidget(self.combobox)
            
        for eachOrder in self.order:
            if eachOrder=="text":
                if message:
                    layout.addWidget(qmessage)
                if not text == False:
                    if textInputLayout:
                        layout.addLayout(textInputLayout)
                    else:
                        layout.addWidget(self.input)
            elif eachOrder=="combobox":
                if comboboxOnTextPosition in ['left', 'right'] and self.combobox:
                    pass
                elif self.combobox:
                    layout.addWidget(self.combobox)
            elif eachOrder=="checkbox":
                if self.checboxList:
                    for thisCheckbox in self.checboxList:
                        layout.addWidget(thisCheckbox)
            elif eachOrder=="radio":
                if self.radioList:
                    rLayout = QtWidgets.QHBoxLayout()
                    for thisRadio in self.radioList:
                        rLayout.addWidget(thisRadio)
                    rLayout.addStretch()
                    layout.addLayout(rLayout)
            
        if vertical:
            buttonLayout = QtWidgets.QVBoxLayout()
        else:
            buttonLayout = QtWidgets.QHBoxLayout()
        self.buttonList = []
        for eachButton in button:
            thisButton = QtWidgets.QPushButton(eachButton, self)
            thisButton.setFocusPolicy(QtCore.Qt.StrongFocus)
            if eachButton.lower() == defaultButton.lower():
                thisButton.setDefault(True)
            thisButton.clicked.connect(partial(self.click, eachButton))
            buttonLayout.addWidget(thisButton)
            self.buttonList.append(thisButton)
        
        layout.addLayout(buttonLayout)

        self.setLayout(layout)
        self.exec_()
        
        toReturn = []
        if self.buttonClicked:
            toReturn.append(self.buttonClicked)
        else:
            toReturn.append(cancelButton)
            
        if not text == False and not readOnly:
            if multiLine:
                value = self.input.toPlainText()
            else:
                value = self.input.text()
        
            if not value:
                value = ""
            
            toReturn.append(value)
        
        if self.combobox:
            toReturn.append(self.combobox.currentText())
        
        cbReturn = []
        if self.checboxList:
            for eachCb in self.checboxList:
                cbReturn.append(eachCb.checkState()==QtCore.Qt.CheckState.Checked)
            toReturn.append(cbReturn)
        
        if self.radioList:
            for eachRadio in self.radioList:
                if eachRadio.isChecked():
                    toReturn.append(eachRadio.text())
                    break
        
        return tuple(toReturn)
        
    def click(self, buttonText):
        self.buttonClicked = buttonText
        self.close()
    
    def checkState(self, validate=None, *args):
        if validate == None:
            return
        
        stateDef = partial(validate, self.input.text())
        state = stateDef()
        
        if state == None:
            color = None
        elif state == True:
            color = "green"
        elif state == False:
            color = "red"
        else:
            color = state
        
        if color:
            self.input.setStyleSheet("QLineEdit {background-color: %s}" % color)
            return
        self.input.setStyleSheet("")
    
    def refreshCompleter(self, *args):
        self.completer.complete()
        
    def updateSuggestion(self, comboboxOnTextPosition='left', *args):
        if not self.suggestion:
            return
        
        val = self.combobox.currentText().lower()
        
        if comboboxOnTextPosition == 'left':
            filteredSuggestion = [a[len(val):] for a in self.suggestion if a.lower().startswith(val) and a[len(val):]]
        else:
            filteredSuggestion = [a[len(val):] for a in self.suggestion if a.lower().endswith(val) and a[len(val):]]
        
        model = self.completer.model()
        model.setStringList(sorted(filteredSuggestion))


try:
    ui.close()
except:
        pass
ui =  AssetFileClean()
def main():
    ui.show()

