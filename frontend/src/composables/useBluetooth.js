import { ref, onUnmounted } from 'vue'

export function useBluetooth() {
    const device = ref(null)
    const server = ref(null)
    const isConnected = ref(false)
    const error = ref(null)
    const heartRate = ref(0)

    // Buffer for batch upload
    const dataBuffer = ref([])
    let bufferTimer = null
    let syncCallback = null // Function to call when buffer is ready

    /**
     * Connect to a standard Heart Rate Monitor (UUID 0x180d)
     */
    const connectDevice = async () => {
        error.value = null
        try {
            // 1. Request Device
            console.log('Requesting Bluetooth Device...')
            device.value = await navigator.bluetooth.requestDevice({
                filters: [{ services: ['heart_rate'] }]
            })

            device.value.addEventListener('gattserverdisconnected', onDisconnected)

            // 2. Connect to Server
            console.log('Connecting to GATT Server...')
            server.value = await device.value.gatt.connect()

            // 3. Get Heart Rate Service
            console.log('Getting Heart Rate Service...')
            const service = await server.value.getPrimaryService('heart_rate')

            // 4. Get Characteristic
            console.log('Getting Characteristic...')
            const characteristic = await service.getCharacteristic('heart_rate_measurement')

            // 5. Start Notifications
            await characteristic.startNotifications()
            characteristic.addEventListener('characteristicvaluechanged', handleCharacteristicValueChanged)

            isConnected.value = true
            startBuffering()
            console.log('Bluetooth Connected!')

        } catch (e) {
            console.error(e)
            error.value = e.message
            isConnected.value = false
        }
    }

    const disconnectDevice = () => {
        if (device.value && device.value.gatt.connected) {
            device.value.gatt.disconnect()
        }
    }

    const onDisconnected = () => {
        console.log('Device Disconnected')
        isConnected.value = false
        stopBuffering()
    }

    /**
     * Parse Heart Rate Measurement (UUID 0x2a37)
     * Flags: 
     *   Bit 0: Heart Rate Value Format (0=UINT8, 1=UINT16)
     */
    const handleCharacteristicValueChanged = (event) => {
        const value = event.target.value
        // First byte is flags
        const flags = value.getUint8(0)

        let hr = 0
        // Check Bit 0
        if (flags & 0x01) {
            // UINT16
            hr = value.getUint16(1, true) // Little Endian
        } else {
            // UINT8
            hr = value.getUint8(1)
        }

        heartRate.value = hr

        // Push to buffer
        if (isConnected.value) {
            dataBuffer.value.push({
                device_type: 'BLE_HRM',
                value: hr,
                unit: 'bpm',
                recorded_at: new Date().toISOString()
            })
        }
    }

    /**
     * Buffer Management
     */
    const startBuffering = () => {
        if (bufferTimer) clearInterval(bufferTimer)
        // Sync every 5 seconds
        bufferTimer = setInterval(() => {
            if (dataBuffer.value.length > 0 && syncCallback) {
                const batch = [...dataBuffer.value]
                dataBuffer.value = [] // Clear immediately
                syncCallback(batch) // Trigger callback
            }
        }, 5000)
    }

    const stopBuffering = () => {
        if (bufferTimer) clearInterval(bufferTimer)
        bufferTimer = null
    }

    const setSyncCallback = (fn) => {
        syncCallback = fn
    }

    onUnmounted(() => {
        stopBuffering()
        disconnectDevice()
    })

    return {
        device,
        isConnected,
        error,
        heartRate,
        connectDevice,
        disconnectDevice,
        setSyncCallback
    }
}
