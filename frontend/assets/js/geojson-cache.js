/**
 * GeoJSON IndexedDB 缓存管理器
 * 解决 localStorage 配额限制问题（25MB GeoJSON 无法存储）
 */
class GeoJSONCacheManager {
    constructor() {
        this.dbName = 'HealthGeoJSONCache';
        this.storeName = 'geojson_data';
        this.version = 1;
        this.db = null;
    }

    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    const store = db.createObjectStore(this.storeName, { keyPath: 'key' });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                }
            };
        });
    }

    async set(key, data, maxAge = 7 * 24 * 60 * 60 * 1000) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            
            const record = {
                key,
                data,
                timestamp: Date.now(),
                maxAge
            };
            
            const request = store.put(record);
            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
        });
    }

    async get(key) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readonly');
            const store = transaction.objectStore(this.storeName);
            const request = store.get(key);
            
            request.onsuccess = () => {
                const record = request.result;
                if (!record) {
                    resolve(null);
                    return;
                }
                
                const age = Date.now() - record.timestamp;
                if (age > record.maxAge) {
                    this.delete(key);
                    resolve(null);
                    return;
                }
                
                console.log(`从 IndexedDB 读取缓存: ${key}, 大小: ${JSON.stringify(record.data).length} 字符`);
                resolve(record.data);
            };
            
            request.onerror = () => reject(request.error);
        });
    }

    async delete(key) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.delete(key);
            
            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
        });
    }

    async clearExpired() {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const index = store.index('timestamp');
            const now = Date.now();
            
            const request = index.openCursor(null);
            const deletedKeys = [];
            
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    const record = cursor.value;
                    if (now - record.timestamp > record.maxAge) {
                        deletedKeys.push(record.key);
                        cursor.delete();
                    }
                    cursor.continue();
                } else {
                    console.log(`清理了 ${deletedKeys.length} 个过期缓存`);
                    resolve(deletedKeys.length);
                }
            };
            
            request.onerror = () => reject(request.error);
        });
    }
}

const geojsonCache = new GeoJSONCacheManager();
