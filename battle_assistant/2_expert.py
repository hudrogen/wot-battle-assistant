import BigWorld
import Avatar
import constants
import Vehicle
from gui.WindowsManager import g_windowsManager
from chat_shared import CHAT_COMMANDS
import CommandMapping
import TriggersManager
from TriggersManager import TRIGGER_TYPE
import random
import string
from gui.battle_control import g_sessionProvider
from debug_utils import *


gExpertTarget = None




oldPlayerAvatar_targetFocus = Avatar.PlayerAvatar.targetFocus
def PlayerAvatar_targetFocus( self, entity ):
    if not isinstance(entity, Vehicle.Vehicle):
        return
    if self.inputHandler.aim:
        self.inputHandler.aim.setTarget(entity)
    isInTutorial = self.arena is not None and self.arena.guiType == constants.ARENA_GUI_TYPE.TUTORIAL
    if (self._PlayerAvatar__isGuiVisible or isInTutorial) and entity.isAlive():
        TriggersManager.g_manager.activateTrigger(TRIGGER_TYPE.AIM_AT_VEHICLE, vehicleId=entity.id)
        if self.team == entity.publicInfo['team']:
            BigWorld.wgAddEdgeDetectEntity(entity, 2)
        else:
            BigWorld.wgAddEdgeDetectEntity(entity, 1)
        global gExpertTarget
        if gExpertTarget is None and self._PlayerAvatar__maySeeOtherVehicleDamagedDevices:
            #print 'PlayerAvatar_targetFocus monitor {0}'.format(entity.id)
            #FLUSH_LOG()
            self.cell.monitorVehicleDamagedDevices(entity.id)

oldPlayerAvatar_targetBlur = Avatar.PlayerAvatar.targetBlur
def PlayerAvatar_targetBlur( self, prevEntity ):
    if not isinstance(prevEntity, Vehicle.Vehicle):
        return
    if self.inputHandler.aim:
        self.inputHandler.aim.clearTarget()
    TriggersManager.g_manager.deactivateTrigger(TRIGGER_TYPE.AIM_AT_VEHICLE)
    BigWorld.wgDelEdgeDetectEntity(prevEntity)
    global gExpertTarget
    if gExpertTarget is None and self._PlayerAvatar__maySeeOtherVehicleDamagedDevices:
        #print 'PlayerAvatar_targetBlur monitor {0}'.format(0)
        #FLUSH_LOG()
        self.cell.monitorVehicleDamagedDevices(0)
        g_windowsManager.battleWindow.damageInfoPanel.hide()

oldPlayerAvatar_showOtherVehicleDamagedDevices = Avatar.PlayerAvatar.showOtherVehicleDamagedDevices
def PlayerAvatar_showOtherVehicleDamagedDevices(self, vehicleID, damagedExtras, destroyedExtras):
    #print 'PlayerAvatar_showOtherVehicleDamagedDevices'
    global gExpertTarget
    target = gExpertTarget or BigWorld.target()
    if target is None or not isinstance(target, Vehicle.Vehicle):
        if self._PlayerAvatar__maySeeOtherVehicleDamagedDevices and vehicleID != 0:
            self.cell.monitorVehicleDamagedDevices(0)
            #print 'PlayerAvatar_showOtherVehicleDamagedDevices monitor {0}'.format(0)
            #FLUSH_LOG()
    elif target.id == vehicleID:
        g_windowsManager.battleWindow.damageInfoPanel.show(vehicleID, damagedExtras, destroyedExtras)
    else:
        if self._PlayerAvatar__maySeeOtherVehicleDamagedDevices:
            self.cell.monitorVehicleDamagedDevices(target.id)
            #print 'PlayerAvatar_showOtherVehicleDamagedDevices monitor {0}'.format(target.id)
            #FLUSH_LOG()
        g_windowsManager.battleWindow.damageInfoPanel.hide()

def setNewTarget(newTarget):
    global gExpertTarget
    #print 'newTarget {0} oldTarget {1}'.format(newTarget, gExpertTarget)
    if newTarget is not gExpertTarget and (newTarget is None or newTarget.isAlive()):
        gExpertTarget = newTarget
        BigWorld.player().cell.monitorVehicleDamagedDevices( gExpertTarget.id if gExpertTarget is not None else 0 )
        #print 'setNewTarget monitor {0}'.format(gExpertTarget.id if gExpertTarget is not None else 0)
        #FLUSH_LOG()
        if g_windowsManager.battleWindow:
            g_windowsManager.battleWindow.pMsgsPanel._FadingMessagesPanel__showMessage(random.choice(string.ascii_letters), 'Expert: {0}'.format(g_sessionProvider.getCtx().getFullPlayerName(vID=gExpertTarget.id)) if gExpertTarget is not None else 'Expert: OFF', 'default')

oldPlayerAvatar_handleKey = Avatar.PlayerAvatar.handleKey
def PlayerAvatar_handleKey(self, isDown, key, mods):
    if self._PlayerAvatar__maySeeOtherVehicleDamagedDevices:
        cmdMap = CommandMapping.g_instance
        #print 'PlayerAvatar_handleKey {0} {1} {2}'.format(cmdMap.isFired(CommandMapping.CMD_CHAT_SHORTCUT_ATTACK, key), isDown, self._PlayerAvatar__maySeeOtherVehicleDamagedDevices)
        if isDown and cmdMap.isFired(CommandMapping.CMD_CHAT_SHORTCUT_ATTACK, key):
            setNewTarget(BigWorld.target())

    return oldPlayerAvatar_handleKey(self, isDown, key, mods)

                                    
oldVehicle_stopVisual = Vehicle.Vehicle.stopVisual
def Vehicle_stopVisual(self):
    oldVehicle_stopVisual( self )

    global gExpertTarget
    if gExpertTarget is not None and self.id == gExpertTarget.id:
        setNewTarget(None)

oldVehicle__onVehicleDeath = Vehicle.Vehicle._Vehicle__onVehicleDeath
def Vehicle__onVehicleDeath(self, isDeadStarted = False):
    oldVehicle__onVehicleDeath(self, isDeadStarted)
    if gExpertTarget is not None and gExpertTarget.id == self.id:
        setNewTarget(None)


oldPlayerAvatar_showShotResults = Avatar.PlayerAvatar.showShotResults
def PlayerAvatar_showShotResults(self, results):
    oldPlayerAvatar_showShotResults(self, results)

    if not self._PlayerAvatar__maySeeOtherVehicleDamagedDevices:
        return

    VHF = constants.VEHICLE_HIT_FLAGS
    for r in results:
        vehicleID = r & 4294967295L
        flags = r >> 32 & 4294967295L
        if flags & VHF.VEHICLE_WAS_DEAD_BEFORE_ATTACK:
            continue
        if flags & VHF.VEHICLE_KILLED:
            return
        setNewTarget(BigWorld.entity(vehicleID))
        return


if BigWorld._ba_config['expert']['enabled']:
    Avatar.PlayerAvatar.targetFocus = PlayerAvatar_targetFocus
    Avatar.PlayerAvatar.targetBlur = PlayerAvatar_targetBlur
    Avatar.PlayerAvatar.showOtherVehicleDamagedDevices = PlayerAvatar_showOtherVehicleDamagedDevices
    Avatar.PlayerAvatar.handleKey = PlayerAvatar_handleKey
    Avatar.PlayerAvatar.showShotResults = PlayerAvatar_showShotResults
    Vehicle.Vehicle.stopVisual = Vehicle_stopVisual
    Vehicle.Vehicle._Vehicle__onVehicleDeath = Vehicle__onVehicleDeath
