const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  getStats:       () => ipcRenderer.invoke('get-stats'),
  getAssignments: () => ipcRenderer.invoke('get-assignments'),
  getPending:     () => ipcRenderer.invoke('get-pending'),
  getCompleted:   () => ipcRenderer.invoke('get-completed'),
  getReminders:   () => ipcRenderer.invoke('get-reminders'),
  openUrl:        (url) => ipcRenderer.invoke('open-url', url),
  winMinimize:    () => ipcRenderer.invoke('win-minimize'),
  winMaximize:    () => ipcRenderer.invoke('win-maximize'),
  winClose:       () => ipcRenderer.invoke('win-close'),
})
