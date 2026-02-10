// static/js/sensorData.js

import { DataManager } from './realtime.js';

/**
 * Inisialisasi DataManager untuk semua modul yang ada
 * @param {string[]} modules - daftar nama modul sesuai endpoint API
 */
export function initSensorModules(modules) {
  // Buat array promise untuk semua inisialisasi
  const initPromises = modules.map(async module => {
    const manager = new DataManager(module);

    DataManager.instances = DataManager.instances || {};
    DataManager.instances[module] = manager;

    await manager.initialize();
    
    console.log(`Module ${module} initialized`);
  });
  
  // Return promise yang resolve ketika semua module sudah diinisialisasi
  return Promise.all(initPromises);
}

/**
 * Dapatkan data terbaru dan buffer per modul
 * @param {string} module - nama modul
 * @returns {object} { latestData, bufferData }
 */
export async function getModuleData(module) {
  const manager = DataManager.instances?.[module];
  if (!manager) {
    console.error(`Module "${module}" belum diinisialisasi`);
    return { latestData: {}, bufferData: {} };
  }
  
  const latestData = await manager.getLatestData();
  const bufferData = {};
  
  // salin buffer untuk seluruh parameter
  manager.dataBuffers.forEach((buf, param) => {
    bufferData[param] = [...buf]; // shallow copy array
  });
  
  return { latestData, bufferData };
}

/**
 * PERBAIKAN: Fungsi processData yang TIDAK menghitung ulang derived data
 * Karena derived data sudah dihitung di DataManager, fungsi ini hanya mengambil data yang sudah ada
 * @param {string} module - nama modul
 * @param {object} data - raw data dari API
 * @returns {object} processed data dengan derived parameters dari buffer
 */
export function processData(module, data) {
  const processed = { ...data };
  const manager = DataManager.instances?.[module];

  if (!manager) {
    console.warn(`Manager for module ${module} not found`);
    return processed;
  }
  

  // TIDAK menghitung ulang untuk menghindari duplikasi
  switch (module) {
    case 'baterai':

      const netCurrentBuffer = manager.dataBuffers.get('battery_net_current') || [];
      if (netCurrentBuffer.length > 0) {
        const latestNetCurrent = netCurrentBuffer[netCurrentBuffer.length - 1];
        processed.battery_net_current = latestNetCurrent.y;
      } else {
        // Fallback jika buffer kosong
        const inputCurrent = processed.battery_input_current || 0;
        const outputCurrent = processed.battery_output_current || 0;
        processed.battery_net_current = inputCurrent - outputCurrent;
      }
      break;
      
    case 'beban':

      const dcPowerBuffer = manager.dataBuffers.get('dc_input_power') || [];
      if (dcPowerBuffer.length > 0) {
        const latestDcPower = dcPowerBuffer[dcPowerBuffer.length - 1];
        processed.dc_input_power = latestDcPower.y;
      } else {
        // Fallback calculation
        const batteryVoltage = processed.battery_voltage || 0;
        const dcCurrent = processed.dc_input_current || 0;
        processed.dc_input_power = batteryVoltage * dcCurrent;
      }
      break;
      
    case 'dump_load':
      // Fallback calculation untuk picohydro charging power
      // Menggunakan picohydro_voltage yang tersedia di dump_load module
      const picoVoltage = processed.picohydro_voltage || 0;
      const picoChargingCurrent = processed.picohydro_charging_current || 0;
      processed.picohydro_charging_power = picoVoltage * picoChargingCurrent;
      
      // Ambil picohydro charging power dari buffer jika ada
      const picoChargingPowerBuffer = manager.dataBuffers.get('picohydro_charging_power') || [];
      if (picoChargingPowerBuffer.length > 0) {
        const latest = picoChargingPowerBuffer[picoChargingPowerBuffer.length - 1];
        processed.picohydro_charging_power = latest.y;
      }
      
      // Fallback calculation untuk dumpload power
      const dumpVoltage = processed.dumpload_voltage || 0;
      const dumpCurrent = processed.dumpload_current || 0;
      processed.dumpload_power = dumpVoltage * dumpCurrent;
      
      // Ambil dumpload power dari buffer jika ada
      const dumploadPowerBuffer = manager.dataBuffers.get('dumpload_power') || [];
      if (dumploadPowerBuffer.length > 0) {
        const latest = dumploadPowerBuffer[dumploadPowerBuffer.length - 1];
        processed.dumpload_power = latest.y;
      }
      break;
      
    case 'picohydro_generator':
      // Ambil picohydro power dari buffer
      const picoPowerBuffer = manager.dataBuffers.get('picohydro_power') || [];
      if (picoPowerBuffer.length > 0) {
        const latest = picoPowerBuffer[picoPowerBuffer.length - 1];
        processed.picohydro_power = latest.y;
      } else {
        // Fallback
        const picoVoltage = processed.picohydro_voltage || 0;
        const picoCurrent = processed.picohydro_current || 0;
        processed.picohydro_power = picoVoltage * picoCurrent;
      }
      break;
      
    case 'solar_panel_generator':
      // Ambil solar power dari buffer
      const solarPowerBuffer = manager.dataBuffers.get('solar_power') || [];
      if (solarPowerBuffer.length > 0) {
        const latest = solarPowerBuffer[solarPowerBuffer.length - 1];
        processed.solar_power = latest.y;
      } else {
        // Fallback
        const solarVoltage = processed.solar_voltage || 0;
        const solarCurrent = processed.solar_current || 0;
        processed.solar_power = solarVoltage * solarCurrent;
      }
      break;
  }
  
  return processed;
}

/**
 * Fungsi khusus untuk mendapatkan data dump_load yang sudah diproses
 * @returns {Promise<object>} Data dump_load dengan perhitungan power
 */
export async function getDumpLoadData() {
  const { latestData, bufferData } = await getModuleData('dump_load');
  const processed = processData('dump_load', latestData);
  
  return {
    latest: processed,
    buffers: bufferData,
    // Tambahan informasi yang berguna
    summary: {
      picohydro_charging_power: processed.picohydro_charging_power || 0,
      dumpload_power: processed.dumpload_power || 0
    }
  };
}

/**
 * PERBAIKAN: Fungsi update yang tidak menghitung ulang derived data
 * @param {string} module - nama modul
 * @param {(latestData: object, bufferData: object)=>void} renderFn
 */
export function startUpdating(module, renderFn) {
  const UPDATE_INTERVAL = 1000; // 1 detik, sama dengan realtime.js
  
  const updateInterval = setInterval(async () => {
    try {
      const { latestData, bufferData } = await getModuleData(module);
      

      // Langsung gunakan data yang sudah termasuk derived parameters dari buffer
      const manager = DataManager.instances?.[module];
      if (manager) {
        // Gabungkan raw data dengan derived data dari buffer
        const processedData = { ...latestData };
        

        manager.dataBuffers.forEach((buffer, param) => {
          if (buffer.length > 0) {
            const latest = buffer[buffer.length - 1];
            processedData[param] = latest.y;
          }
        });
        
        if (Object.keys(processedData).length > 0) {
          renderFn(processedData, bufferData);
        } else {
          console.warn(`No data available for module ${module}`);
        }
      }
    } catch (e) {
      console.error(`Error updating module ${module}:`, e);
    }
  }, UPDATE_INTERVAL);
  
  // Return interval ID sehingga bisa di-clear jika perlu
  return updateInterval;
}

/**
 * UTILITY: Fungsi untuk mendapatkan parameter yang tersedia untuk suatu modul
 * @param {string} module - nama modul
 * @returns {string[]} array nama parameter
 */
export function getAvailableParameters(module) {
  const manager = DataManager.instances?.[module];
  if (!manager) {
    return [];
  }
  
  return Array.from(manager.dataBuffers.keys());
}

/**
 * UTILITY: Fungsi untuk mendapatkan data spesifik parameter
 * @param {string} module - nama modul
 * @param {string} parameter - nama parameter
 * @returns {array} array data points {x: timestamp, y: value}
 */
export function getParameterData(module, parameter) {
  const manager = DataManager.instances?.[module];
  if (!manager) {
    return [];
  }
  
  return manager.getData(parameter);
}

/**
 * UTILITY: Fungsi untuk debugging - menampilkan status semua buffer
 * @param {string} module - nama modul
 */
export function debugBufferStatus(module) {
  const manager = DataManager.instances?.[module];
  if (!manager) {
    console.log(`No manager found for module: ${module}`);
    return;
  }
  
  console.log(`=== Buffer Status for ${module} ===`);
  manager.dataBuffers.forEach((buffer, param) => {
    console.log(`${param}: ${buffer.length} points`);
    if (buffer.length > 0) {
      const latest = buffer[buffer.length - 1];
      const oldest = buffer[0];
      console.log(`  Latest: ${latest.y} at ${new Date(latest.x * 1000).toLocaleTimeString()}`);
      console.log(`  Oldest: ${oldest.y} at ${new Date(oldest.x * 1000).toLocaleTimeString()}`);
    }
  });
  console.log(`==============================`);
}
