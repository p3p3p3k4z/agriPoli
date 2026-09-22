

document.addEventListener('DOMContentLoaded', function() {
  const paths = document.querySelectorAll('.mexico-cifras__mapa path');
  const stateNameElement = document.getElementById('stateName');
  const ndviValue = document.getElementById('ndviValue');
  const nbrValue = document.getElementById('nbrValue');
  const eviValue = document.getElementById('eviValue');
  const vegetationStatus = document.getElementById('vegetationStatus');
  const stateModal = new bootstrap.Modal(document.getElementById('stateModal'));

paths.forEach(path => {
  path.addEventListener('click', async function() {
    paths.forEach(p => p.classList.remove('active'));
    this.classList.add('active');

    const stateName = this.getAttribute('data-estado') || this.querySelector('title')?.textContent || 'Estado desconocido';
    const stateId = this.getAttribute('data-id');

    stateNameElement.textContent = stateName;

    ndviValue.textContent = nbrValue.textContent = eviValue.textContent = '--';
    vegetationStatus.textContent = 'Cargando datos...';
    vegetationStatus.className = 'alert alert-secondary';
    const analysisResult = document.getElementById('analysisResult');
    analysisResult.innerHTML = '<p class="text-muted">Analizando información...</p>';
    stateModal.show();

    const data = await getDatosVegetation(stateName);

    if (data) {
      const answer = await analizarParametros(data[0].NDVI, data[0].NBR, data[0].EVI, stateName);
      console.log('Respuesta del análisis de parámetros:', answer);

      ndviValue.textContent = data[0].NDVI?.toFixed(2) ?? '--';
      nbrValue.textContent = data[0].NBR?.toFixed(2) ?? '--';
      eviValue.textContent = data[0].EVI?.toFixed(2) ?? '--';

      const mensaje = interpretarVegetacion(data[0].NDVI, data[0].NBR, data[0].EVI);
      vegetationStatus.textContent = mensaje.texto;
      vegetationStatus.className = `alert ${mensaje.clase}`;

      // 🔹 Mostrar resultado detallado del análisis (HTML del backend)
      if (answer) {
        analysisResult.innerHTML = answer;
      } else {
        analysisResult.innerHTML = '<p class="text-muted">No se pudo generar un análisis detallado.</p>';
      }

    } else {
      vegetationStatus.textContent = 'No se pudieron obtener datos.';
      vegetationStatus.className = 'alert alert-danger';
      analysisResult.innerHTML = '<p class="text-danger">No se pudo obtener información del análisis.</p>';
    }
  });
});

});

async function getDatosVegetation(state) {
  try {
    const response = await fetch(`http://localhost:3000/api/vegetation/${state}`);
    console.log(`Fetch URL: http://localhost:3000/api/vegetation/${state}`);
    if (!response.ok) throw new Error('Error en la respuesta');
    const data = await response.json();
    console.log('Datos de vegetación:', data['data']);
    return data['data'];
  } catch (error) {
    console.error('Error al obtener datos de vegetación:', error);
    return null;
  }
}

async function analizarParametros(ndvi, nbr, evi,state) {

  try {
    promt = `NDVI: ${ndvi}, NBR: ${nbr}, EVI: ${evi}, Estado: ${state}`;
    const response = await fetch(`http://localhost:3000/api/gemeni/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: promt }),
    });
    if (!response.ok) throw new Error('Error en la respuesta');
    const data = await response.json();
    const newdata = data.answer.slice(7,-3);
    return newdata;
  } catch (error) {
    console.error('Error al analizar parámetros:', error);
    return null;
  }
  
}


/**
 * Analiza los valores NDVI, NBR y EVI y devuelve un mensaje descriptivo
 */
function interpretarVegetacion(ndvi, nbr, evi) {
  // Definir umbrales aproximados
  console.log('Interpretando valores:', { ndvi, nbr, evi });
  if (ndvi === undefined || nbr === undefined || evi === undefined) {
    return { texto: 'Datos insuficientes para interpretar.', clase: 'alert-warning' };
  }
  const ndviAlto = ndvi >= 0.6;
  const ndviBajo = ndvi < 0.2;
  const nbrAlto = nbr > 0.2;
  const nbrBajo = nbr < -0.1;
  const eviAlto = evi >= 0.5;
  const eviBajo = evi <= 0.2;

  // Caso 1: Crecimiento
  if (ndviAlto && nbrAlto) {
    return { texto: '🌿 Las plantas están en crecimiento.', clase: 'alert-success' };
  }
  // Caso 2: Enfermedad o estrés hídrico
  else if (ndviBajo && nbrBajo && !eviBajo) {
    return { texto: '⚠️ Posible enfermedad o estrés hídrico.', clase: 'alert-warning' };
  }
  // Caso 3: Envejecimiento
  else if (ndviBajo && nbrBajo && eviBajo) {
    return { texto: '🍂 Envejecimiento de las plantas.', clase: 'alert-secondary' };
  }
  // Caso 4: Floración
  else if (ndviAlto && eviAlto && nbrBajo) {
    return { texto: '🌸 Etapa de floración.', clase: 'alert-info' };
  }
  // Caso general
  else {
    //return { texto: '🔍 Estado intermedio o no definido claramente.', clase: 'alert-light' };
  }
}
