// Simulate browser environment
const fs = require('fs');

const elements = {};
function createElement(id, tagName = 'div') {
    return {
        id,
        tagName,
        style: {},
        getContext: () => ({
            clearRect: () => {},
            drawImage: () => {},
            strokeRect: () => {},
            fillRect: () => {},
            fillText: () => {}
        }),
        classList: {
            add: (cls) => console.log(`[classList.add] #${id} .${cls}`),
            remove: (cls) => console.log(`[classList.remove] #${id} .${cls}`),
            toggle: (cls, val) => console.log(`[classList.toggle] #${id} .${cls} = ${val}`)
        },
        querySelectorAll: () => [],
        querySelector: (sel) => null,
        addEventListener: () => {},
        setAttribute: () => {},
        getAttribute: () => '',
        innerHTML: '',
        textContent: '',
        value: ''
    };
}

const mockDoc = {
    addEventListener: (event, cb) => {
        if (event === 'DOMContentLoaded') {
            mockDoc._domReady = cb;
        }
    },
    getElementById: (id) => {
        if (!elements[id]) {
            elements[id] = createElement(id);
        }
        return elements[id];
    },
    querySelectorAll: (sel) => [],
    querySelector: (sel) => null
};

global.window = {
    scrollTo: () => {},
    addEventListener: () => {},
    localStorage: {
        getItem: () => null,
        setItem: () => {}
    },
    setInterval: (cb, ms) => {},
    setTimeout: (cb, ms) => { cb(); },
    location: { reload: () => {} }
};
global.document = mockDoc;
global.fetch = async (url) => {
    console.log('[fetch called]', url);
    if (url === '/api/auth/me') {
        return {
            ok: true,
            json: async () => ({
                authenticated: true,
                user: { id: 20, full_name: 'Abebe Kebede', email: 'abebe.kebede@gamewatch.et', role: 'OWNER' }
            })
        };
    }
    return {
        ok: true,
        json: async () => ({})
    };
};

try {
    const code = fs.readFileSync('static/js/app.js', 'utf8');
    eval(code);
    console.log('[EVAL OK]');
    if (mockDoc._domReady) {
        console.log('[TRIGGERING DOMContentLoaded]');
        mockDoc._domReady();
        console.log('[DOMContentLoaded COMPLETE]');
    }
} catch (e) {
    console.error('[ERROR IN APP.JS]', e);
}
