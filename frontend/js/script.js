document.addEventListener('DOMContentLoaded', () => {
    const modelViewer = document.getElementById('island-viewer');

    // ====================================================================================
    // BASE DE DATOS ECOSISTÉMICA REGIONAL
    // ====================================================================================
    const stateData = {
        "Oaxaca": {
            modelSrc: "modelos/isla_oaxaca.glb",
            infoCompleta: {
                titulo: "Isla Polinizadora – Oaxaca",
                contexto: {
                    ubicacion: "Valles Centrales y Sierra Sur, Oaxaca, México",
                    climas: "Templado subhúmedo, tropical seco y estacional.",
                    usosAgricolas: [
                        "Maíz criollo",
                        "Café de sombra",
                        "Agave mezcalero (Espadín, Tobalá)",
                        "Frutales de traspatio",
                        "Frijol y calabaza (Milpa tradicional)",
                        "Hortalizas orgánicas"
                    ],
                    reto: "Fragmentación de hábitats, uso de pesticidas sintéticos y estrés hídrico durante la temporada seca."
                },
                polinizadores: {
                    titulo: "Polinizadores Clave",
                    especies: [
                        { nombre: "Abeja Melipona", cientifico: "Melipona beecheii", tipo: "Nativa sin aguijón", rol: "Especialista en cultivos tradicionales y flora nativa.", accent: "accent-yellow" },
                        { nombre: "Abeja Europea", cientifico: "Apis mellifera", tipo: "Generalista", rol: "Polinización masiva de floraciones abiertas y frutales.", accent: "accent-orange" },
                        { nombre: "Mariposa Monarca", cientifico: "Danaus plexippus", tipo: "Lepidóptero migratorio", rol: "Polinización cruzada en corredores de altura.", accent: "accent-orange" },
                        { nombre: "Colibrí Corona Violeta", cientifico: "Ramosomyia violiceps", tipo: "Avispa / Picaflor", rol: "Polinización de flores tubulares rojas y naranjas.", accent: "accent-purple" },
                        { nombre: "Abejorro Nativo", cientifico: "Bombus ephippiatus", tipo: "Himenóptero robusto", rol: "Polinización por zumbido (buzz pollination) en solanáceas.", accent: "accent-yellow" }
                    ]
                },
                flores: {
                    titulo: "Flores y Estratos Herbáceos",
                    beneficios: "Suministro ininterrumpido de néctar y polen, microclima húmedo y supresión biológica de malezas.",
                    especies: [
                        { nombre: "Dalia Silvestre", cientifico: "Dahlia coccinea", funcion: "Flor nacional de México; atracción cromática intensa y néctar abundante.", accent: "accent-yellow" },
                        { nombre: "Cempasúchil", cientifico: "Tagetes erecta", funcion: "Atracción floral masiva y acción nematicida natural en el suelo.", accent: "accent-orange" },
                        { nombre: "Salvia Mexicana", cientifico: "Salvia mexicana", funcion: "Corolas tubulares de alta atracción para colibríes y abejorros.", accent: "accent-purple" },
                        { nombre: "Flor de Mayo", cientifico: "Plumeria rubra", funcion: "Fragancia nocturna y diurna para polinizadores medianos y esfíngidos.", accent: "accent-green" },
                        { nombre: "Zinnia Elegante", cientifico: "Zinnia elegans", funcion: "Floración prolongada, resistente al sol directo y sequía.", accent: "accent-yellow" },
                        { nombre: "Cosmos Silvestre", cientifico: "Cosmos sulphureus", funcion: "Fácil establecimiento, producción copiosa de polen accesible.", accent: "accent-orange" },
                        { nombre: "Albahaca Silvestre", cientifico: "Ocimum micranthum", funcion: "Aroma repelente de plagas y atracción continua de abejas nativas.", accent: "accent-green" }
                    ]
                },
                dosel: {
                    titulo: "Dosel Arbóreo (Árboles Protectores)",
                    beneficios: "Fijación activa de nitrógeno, barrera cortaviento, captura de carbono y néctar estacional.",
                    especies: [
                        { nombre: "Mezquite", cientifico: "Prosopis laevigata", funcion: "Resiliente a sequía extrema, nodriza de suelos y miel de alta calidad.", accent: "accent-green" },
                        { nombre: "Tepehuaje", cientifico: "Lysiloma acapulcense", funcion: "Leguminosa fijadora de nitrógeno; floración melífera profusa.", accent: "accent-green" },
                        { nombre: "Guaje Blanco", cientifico: "Leucaena leucocephala", funcion: "Mejora rápida de suelos degradados, forraje y floración temprana.", accent: "accent-green" },
                        { nombre: "Copal Santo", cientifico: "Bursera bipinnata", funcion: "Aporte de resinas aromáticas, néctar y refugio de insectos nocturnos.", accent: "accent-blue" },
                        { nombre: "Guayabo Criollo", cientifico: "Psidium guajava", funcion: "Flores blancas muy visitadas por abejas; frutos para fauna local.", accent: "accent-green" },
                        { nombre: "Zapote Negro", cientifico: "Diospyros digyna", funcion: "Estructura de sombra profunda y soporte para epífitas y lianas.", accent: "accent-green" }
                    ]
                },
                auxiliares: {
                    titulo: "Insectos Auxiliares y Control Biológico",
                    beneficios: "Equilibrio trófico sin plaguicidas, depredación de plagas y aceleración del ciclo de nutrientes.",
                    especies: [
                        { nombre: "Mariquita Convergente", cientifico: "Hippodamia convergens", funcion: "Depredador activo de pulgones, trips y ácaros dañinos.", accent: "accent-orange" },
                        { nombre: "Crisopa Verde", cientifico: "Chrysoperla carnea", funcion: "Larvas voraces ('leones de pulgones') que barren plagas agrícolas.", accent: "accent-green" },
                        { nombre: "Escarabajo Estercolero", cientifico: "Scarabaeidae", funcion: "Reciclaje de materia orgánica, aireación y descompactación edáfica.", accent: "accent-blue" },
                        { nombre: "Avispa Parasitoide", cientifico: "Trichogramma spp.", funcion: "Control micro-biológico de orugas barrenadoras en maíz.", accent: "accent-purple" }
                    ]
                },
                infraestructura: {
                    titulo: "Infraestructura del Hábitat",
                    elementos: [
                        { nombre: "Hotel de Insectos y Abejas Solitarias", desc: "Bloques de madera no tratada con perforaciones de 4 a 8 mm, cañas de carrizo y barro para anidación." },
                        { nombre: "Estación de Abrevadero Seguro", desc: "Platos someros con piedras y guijarros que permiten a las abejas y mariposas beber agua sin riesgo de ahogarse." },
                        { nombre: "Franja de Suelo Desnudo Arcilloso", desc: "Área protegida sin mantillo para que abejas mineras nativas y avispas alfareras colecten material y aniden." },
                        { nombre: "Módulo de Compostaje Dinámico", desc: "Reintegración de restos de podas y hojarasca para alimentar microorganismos y lombrices nativas." }
                    ]
                }
            }
        }
        /*
        ====================================================================================
        REGIONES CHIAPAS Y GUERRERO DESACTIVADAS (Comentadas por requerimiento del usuario)
        ====================================================================================
        "Chiapas": {
            modelSrc: "modelos/isla_chiapas.glb",
            infoCompleta: { ... }
        },
        "Guerrero": {
            modelSrc: "modelos/isla_guerrero.glb",
            infoCompleta: { ... }
        }
        */
    };

    // ====================================================================================
    // RENDERIZADO DEL MOSAICO (OAXACA)
    // ====================================================================================
    function renderMosaic(oaxacaData) {
        const info = oaxacaData.infoCompleta;

        // 1. Render 3D Model
        if (modelViewer && oaxacaData.modelSrc) {
            modelViewer.src = oaxacaData.modelSrc;
        }

        // 2. Mosaico Cultivos & Contexto
        const cultivosContainer = document.getElementById('mosaic-cultivos');
        if (cultivosContainer) {
            cultivosContainer.innerHTML = `
                <div class="mosaic-title">
                    <span class="pill pill-yellow">AGROECOSISTEMA</span>
                    <h3>Cultivos & Contexto</h3>
                </div>
                <p><strong>Ubicación:</strong> ${info.contexto.ubicacion}</p>
                <p style="margin-top: 0.3rem;"><strong>Clima:</strong> ${info.contexto.climas}</p>
                
                <h4 style="margin-top: 0.75rem; font-size: 0.9rem;">Cultivos Protegidos:</h4>
                <div class="tag-cloud">
                    ${info.contexto.usosAgricolas.map(c => `<span class="tag tag-highlight">${c}</span>`).join('')}
                </div>
                
                <div class="note-box">
                    <strong>Reto Agroecológico:</strong> ${info.contexto.reto}
                </div>
            `;
        }

        // 3. Mosaico Polinizadores
        const polinizadoresContainer = document.getElementById('mosaic-polinizadores');
        if (polinizadoresContainer) {
            polinizadoresContainer.innerHTML = `
                <div class="mosaic-title">
                    <span class="pill pill-orange">ENTOMOLOGÍA</span>
                    <h3>${info.polinizadores.titulo}</h3>
                </div>
                <p style="font-size: 0.85rem; margin-bottom: 0.5rem;">Especies fundamentales para la productividad agrícola en Oaxaca:</p>
                <div class="mosaic-card-list">
                    ${info.polinizadores.especies.map(p => `
                        <div class="species-card ${p.accent}">
                            <div class="species-card-head">
                                <span class="species-name">${p.nombre}</span>
                                <span class="species-scientific">${p.cientifico}</span>
                            </div>
                            <p class="species-role">${p.rol}</p>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // 4. Mosaico Flores y Estrato Herbáceo
        const floresContainer = document.getElementById('mosaic-flores');
        if (floresContainer) {
            floresContainer.innerHTML = `
                <div class="mosaic-title">
                    <span class="pill pill-yellow">ESTRATO HERBÁCEO</span>
                    <h3>${info.flores.titulo}</h3>
                </div>
                <p style="font-size: 0.85rem; margin-bottom: 0.4rem;">${info.flores.beneficios}</p>
                <div class="mosaic-card-grid">
                    ${info.flores.especies.map(f => `
                        <div class="species-card ${f.accent}">
                            <div class="species-card-head">
                                <span class="species-name">${f.nombre}</span>
                                <span class="species-scientific">${f.cientifico}</span>
                            </div>
                            <p class="species-role">${f.funcion}</p>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // 5. Mosaico Árboles y Dosel
        const arbolesContainer = document.getElementById('mosaic-arboles');
        if (arbolesContainer) {
            arbolesContainer.innerHTML = `
                <div class="mosaic-title">
                    <span class="pill pill-green">ESTRATO ARBÓREO</span>
                    <h3>${info.dosel.titulo}</h3>
                </div>
                <p style="font-size: 0.85rem; margin-bottom: 0.4rem;">${info.dosel.beneficios}</p>
                <div class="mosaic-card-grid">
                    ${info.dosel.especies.map(a => `
                        <div class="species-card ${a.accent}">
                            <div class="species-card-head">
                                <span class="species-name">${a.nombre}</span>
                                <span class="species-scientific">${a.cientifico}</span>
                            </div>
                            <p class="species-role">${a.funcion}</p>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // 6. Mosaico Auxiliares
        const auxiliaresContainer = document.getElementById('mosaic-auxiliares');
        if (auxiliaresContainer) {
            auxiliaresContainer.innerHTML = `
                <div class="mosaic-title">
                    <span class="pill pill-purple">CONTROL BIOLÓGICO</span>
                    <h3>${info.auxiliares.titulo}</h3>
                </div>
                <p style="font-size: 0.85rem; margin-bottom: 0.4rem;">${info.auxiliares.beneficios}</p>
                <div class="mosaic-card-grid">
                    ${info.auxiliares.especies.map(aux => `
                        <div class="species-card ${aux.accent}">
                            <div class="species-card-head">
                                <span class="species-name">${aux.nombre}</span>
                                <span class="species-scientific">${aux.cientifico}</span>
                            </div>
                            <p class="species-role">${aux.funcion}</p>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // 7. Mosaico Infraestructura
        const infraContainer = document.getElementById('mosaic-infraestructura');
        if (infraContainer) {
            infraContainer.innerHTML = `
                <div class="mosaic-title">
                    <span class="pill pill-blue">HÁBITAT & BIOESTRUCTURA</span>
                    <h3>${info.infraestructura.titulo}</h3>
                </div>
                <div class="mosaic-card-grid">
                    ${info.infraestructura.elementos.map(item => `
                        <div class="species-card accent-blue">
                            <span class="species-name" style="display: block; margin-bottom: 0.25rem;">${item.nombre}</span>
                            <p class="species-role">${item.desc}</p>
                        </div>
                    `).join('')}
                </div>
            `;
        }
    }

    // Inicializar con Oaxaca
    renderMosaic(stateData["Oaxaca"]);
});