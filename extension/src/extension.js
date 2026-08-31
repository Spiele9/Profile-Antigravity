const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { parseAntigravityProfile } = require('./parser');

/**
 * Antigravity Profile View Provider
 */
class AntigravityProfileViewProvider {
  constructor(context) {
    this._context = context;
    this._view = null;
  }

  async resolveWebviewView(webviewView, context, _token) {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [
        vscode.Uri.file(path.join(this._context.extensionPath, 'assets')),
        vscode.Uri.file(path.join(this._context.extensionPath, 'webview'))
      ]
    };

    // Load custom user preferences from globalState
    const customUser = this._context.globalState.get('antigravity_profile_user', null);
    const profileData = await parseAntigravityProfile(customUser);

    webviewView.webview.html = this._getHtmlForWebview(webviewView.webview, profileData);

    // Listen for messages from the webview
    webviewView.webview.onDidReceiveMessage(async (message) => {
      switch (message.type) {
        case 'refresh': {
          await this.refresh();
          break;
        }
        case 'saveUser': {
          await this._context.globalState.update('antigravity_profile_user', message.data);
          vscode.window.showInformationMessage('Antigravity profile updated!');
          await this.refresh();
          break;
        }
        case 'showToast': {
          vscode.window.showInformationMessage(message.text || 'Notification');
          break;
        }
      }
    });
  }

  async refresh() {
    if (!this._view) return;
    try {
      const customUser = this._context.globalState.get('antigravity_profile_user', null);
      const profileData = await parseAntigravityProfile(customUser);
      this._view.webview.postMessage({
        type: 'updateProfileData',
        data: profileData
      });
    } catch (e) {
      vscode.window.showErrorMessage(`Failed to refresh profile: ${e.message}`);
    }
  }

  _getHtmlForWebview(webview, profileData) {
    // Read the base template from webview/profile.html or assets
    const htmlPath = path.join(this._context.extensionPath, 'webview', 'profile.html');
    let template = '';
    if (fs.existsSync(htmlPath)) {
      template = fs.readFileSync(htmlPath, 'utf8');
      // Inject initial profileData into the script block
      const jsonStr = JSON.stringify(profileData);
      template = template.replace(
        /const profileData = \{.*?\};/s,
        `const profileData = ${jsonStr};`
      );
    } else {
      template = `<!DOCTYPE html><html><body><h3>Antigravity Profile Loading...</h3></body></html>`;
    }

    // Add VS Code API messaging bridge script
    const bridgeScript = `
      <script>
        const vscodeApi = (typeof acquireVsCodeApi === 'function') ? acquireVsCodeApi() : null;
        
        window.addEventListener('message', event => {
          const msg = event.data;
          if (msg.type === 'updateProfileData' && msg.data) {
            Object.assign(profileData, msg.data);
            if (typeof applyProfileHeader === 'function') applyProfileHeader();
            if (typeof renderPlugins === 'function') renderPlugins();
            if (typeof renderHeatmap === 'function') renderHeatmap();
          }
        });

        // Override saveProfile to communicate with VS Code extension
        const originalSaveProfile = window.saveProfile;
        window.saveProfile = function() {
          if (typeof originalSaveProfile === 'function') originalSaveProfile();
          if (vscodeApi) {
            vscodeApi.postMessage({
              type: 'saveUser',
              data: profileData.user
            });
          }
        };

        // Override refresh to trigger native Node.js parser
        const originalRefresh = window.refreshProfileStats;
        window.refreshProfileStats = function() {
          if (typeof originalRefresh === 'function') originalRefresh();
          if (vscodeApi) {
            vscodeApi.postMessage({ type: 'refresh' });
          }
        };
      </script>
    `;

    return template.replace('</body>', `${bridgeScript}</body>`);
  }
}

/**
 * Extension Activate Function
 */
function activate(context) {
  const provider = new AntigravityProfileViewProvider(context);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider('antigravity.profileView', provider, {
      webviewOptions: { retainContextWhenHidden: true }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('antigravity.refreshProfile', () => {
      provider.refresh();
    })
  );
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
