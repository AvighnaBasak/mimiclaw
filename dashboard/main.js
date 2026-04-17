const { app, BrowserWindow, ipcMain, shell } = require('electron')
const path = require('path')
const { execFile } = require('child_process')
const { promisify } = require('util')

const execFileAsync = promisify(execFile)
const ROOT_DIR = path.join(__dirname, '..')
const BRIDGE = path.join(ROOT_DIR, 'db_bridge.py')

async function queryDb(queryType) {
  try {
    const { stdout } = await execFileAsync('python', [BRIDGE, queryType], {
      cwd: ROOT_DIR,
      timeout: 15000,
    })
    return JSON.parse(stdout.trim())
  } catch (err) {
    console.error(`db_bridge error [${queryType}]:`, err.message)
    return queryType === 'stats'
      ? { total: 0, completed: 0, pending: 0, overdue: 0 }
      : []
  }
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    title: 'MimiClaw Dashboard',
    backgroundColor: '#F5F5F0',
  })

  win.loadFile(path.join(__dirname, 'index.html'))

  // Open external links in browser, not Electron
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  app.quit()
})

ipcMain.handle('get-stats', () => queryDb('stats'))
ipcMain.handle('get-assignments', () => queryDb('assignments'))
ipcMain.handle('get-pending', () => queryDb('pending'))
ipcMain.handle('get-completed', () => queryDb('completed'))
ipcMain.handle('get-reminders', () => queryDb('reminders'))

ipcMain.handle('open-url', (_event, url) => {
  if (url && url.startsWith('https://')) shell.openExternal(url)
})
