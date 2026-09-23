document.addEventListener('DOMContentLoaded', () => {
    const modelViewer = document.getElementById('island-viewer');
    const headerRegionLabel = document.getElementById('headerRegionLabel');
    const viewerTitle = document.getElementById('viewerTitle');
    const modelFilenameTag = document.getElementById('modelFilenameTag');
    const progressFill = document.getElementById('modelProgressFill');
    const btnToggleRotate = document.getElementById('btnToggleRotate');
    const btnResetCamera = document.getElementById('btnResetCamera');
    const btnFullscreen3D = document.getElementById('btnFullscreen3D');
    const viewerWrapper = document.getElementById('viewerWrapper');

    // ====================================================================================
    // DATOS AGRÍCOLAS Y PLANTAS POR REGIÓN (OAXACA, CHIAPAS, GUERRERO)
    // ====================================================================================
    const stateData = {
        "Oaxaca": {
            modelSrc: "modelos/isla_oaxaca.glb",
            infoCompleta: {
                titulo: "Isla de Cultivo – Oaxaca",
                contexto: {
                    ubicacion: "Valles Centrales y Sierra Sur, Oaxaca, México",
                    climas: "Clima templado en la sierra y cálido en los valles, con época de secas marcada.",
                    usosAgricolas: [
                        "Maíz nativo",
                        "Café de sombra",
                        "Maguey para mezcal (Espadín y Tobalá)",
                        "Frutas de huerto",
                        "Frijol y calabaza (Milpa)",
                        "Hortalizas y verduras"
                    ],
                    reto: "Escasez de agua en los meses secos y necesidad de cuidar a las abejas de los químicos agrícolas."
                },
                polinizadores: {
                    titulo: "Polinizadores de la zona",
                    especies: [
                        { nombre: "Abeja Melipona", cientifico: "Melipona beecheii", tipo: "Abeja nativa sin aguijón", rol: "Muy dócil; poliniza flores de la huerta y plantas locales.", accent: "accent-yellow" },
                        { nombre: "Abeja de Miel", cientifico: "Apis mellifera", tipo: "Abeja común", rol: "Poliniza árboles frutales y gran variedad de flores de campo.", accent: "accent-orange" },
                        { nombre: "Mariposa Monarca", cientifico: "Danaus plexippus", tipo: "Mariposa viajera", rol: "Visita y fertiliza flores a lo largo de sus rutas de vuelo.", accent: "accent-orange" },
                        { nombre: "Colibrí Corona Violeta", cientifico: "Ramosomyia violiceps", tipo: "Picaflor", rol: "Le encantan las flores alargadas rojas y naranjas.", accent: "accent-purple" },
                        { nombre: "Abejorro de Campo", cientifico: "Bombus ephippiatus", tipo: "Abejorro grande", rol: "Hace vibrar las flores de jitomate y chile para que suelten el polen.", accent: "accent-yellow" }
                    ]
                },
                flores: {
                    titulo: "Flores y plantas bajas",
                    beneficios: "Dan néctar y polen todo el año, mantienen fresca la tierra y no dejan crecer hierba mala.",
                    especies: [
                        { nombre: "Dalia Silvestre", cientifico: "Dahlia coccinea", funcion: "Flor nacional; sus colores vivos atraen muchas abejas y mariposas.", accent: "accent-yellow" },
                        { nombre: "Cempasúchil", cientifico: "Tagetes erecta", funcion: "Atrae polinizadores y sus raíces ahuyentan plagas del suelo.", accent: "accent-orange" },
                        { nombre: "Salvia Morada", cientifico: "Salvia mexicana", funcion: "Flores en tubo que alimentan a colibríes y abejorros.", accent: "accent-purple" },
                        { nombre: "Flor de Mayo", cientifico: "Plumeria rubra", funcion: "Aroma dulce de día y noche que atrae mariposas y polinizadores.", accent: "accent-green" },
                        { nombre: "Zinnia de Colores", cientifico: "Zinnia elegans", funcion: "Aguanta el sol fuerte, resiste la falta de agua y florece por meses.", accent: "accent-yellow" },
                        { nombre: "Cosmos Silvestre", cientifico: "Cosmos sulphureus", funcion: "Nace rápido y produce mucho polen fácil de alcanzar para las abejas.", accent: "accent-orange" },
                        { nombre: "Albahaca de Campo", cientifico: "Ocimum micranthum", funcion: "Su olor ahuyenta insectos dañinos y atrae abejas benéficas.", accent: "accent-green" }
                    ]
                },
                dosel: {
                    titulo: "Árboles de sombra",
                    beneficios: "Nutren la tierra de forma natural, frenan vientos fuertes y dan sombra fresca al cultivo.",
                    especies: [
                        { nombre: "Mezquite", cientifico: "Prosopis laevigata", funcion: "Resiste sequías duras, mejora el suelo y de sus flores sale miel clara.", accent: "accent-green" },
                        { nombre: "Tepehuaje", cientifico: "Lysiloma acapulcense", funcion: "Abona la tierra de forma natural y da muchísimas flores para las abejas.", accent: "accent-green" },
                        { nombre: "Guaje Blanco", cientifico: "Leucaena leucocephala", funcion: "Mejora tierras desgastadas, da forraje y florece desde muy joven.", accent: "accent-green" },
                        { nombre: "Copal", cientifico: "Bursera bipinnata", funcion: "Da resina de olor agradable y sirve de hogar para pájaros e insectos.", accent: "accent-blue" },
                        { nombre: "Guayabo", cientifico: "Psidium guajava", funcion: "Flores blancas muy visitadas por abejas y frutos dulces comestibles.", accent: "accent-green" },
                        { nombre: "Zapote Negro", cientifico: "Diospyros digyna", funcion: "Árbol grande y frondoso que da sombra profunda y frutos.", accent: "accent-green" }
                    ]
                },
                auxiliares: {
                    titulo: "Insectos que ayudan contra plagas",
                    beneficios: "Mantienen la huerta sana comiéndose a las plagas sin necesidad de químicos.",
                    especies: [
                        { nombre: "Mariquita", cientifico: "Hippodamia convergens", funcion: "Se come los pulgones y pequeños ácaros que dañan las hojas tiernas.", accent: "accent-orange" },
                        { nombre: "Crisopa Verde", cientifico: "Chrysoperla carnea", funcion: "Sus crías son excelentes cazadoras de bichos que arruinan la cosecha.", accent: "accent-green" },
                        { nombre: "Escarabajo de Suelo", cientifico: "Scarabaeidae", funcion: "Entierra materia orgánica, afloja la tierra y ayuda a que respire.", accent: "accent-blue" },
                        { nombre: "Avispa Amiga", cientifico: "Trichogramma spp.", funcion: "Ataca a los gusanos que barrenan las mazorcas de maíz.", accent: "accent-purple" }
                    ]
                },
                infraestructura: {
                    titulo: "Agua, nidos y abono",
                    elementos: [
                        { nombre: "Nido de madera para abejas", desc: "Bloques de madera con agujeros de 4 a 8 mm y cañas secas donde las abejas solitarias pueden anidar seguras." },
                        { nombre: "Bebedero con piedras", desc: "Plato con agua y piedritas donde las abejas y mariposas pueden posarse y tomar agua sin peligro de ahogarse." },
                        { nombre: "Tierra suelta para nidos", desc: "Pequeño espacio de tierra limpia donde abejas y avispas recolectan lodo para construir sus nidos." },
                        { nombre: "Montón de composta", desc: "Hojas secas y restos de podas que se fermentan para abonar las plantas y alimentar lombrices." }
                    ]
                }
            }
        },
        "Chiapas": {
            modelSrc: "modelos/isla_chiapas.glb",
            infoCompleta: {
                titulo: "Isla de Cultivo – Chiapas",
                contexto: {
                    ubicacion: "Selva Lacandona, Soconusco y Altos de Chiapas, México",
                    climas: "Cálido y húmedo con lluvias abundantes en la selva, y clima fresco en las montañas.",
                    usosAgricolas: [
                        "Cacao criollo de aroma fino",
                        "Café de sombra de altura",
                        "Plátano criollo",
                        "Milpa tradicional de selva",
                        "Vainilla de monte",
                        "Cardamomo"
                    ],
                    reto: "Cuidar los caminos de paso de animales y manejar la humedad alta para que no salgan hongos en las hojas."
                },
                polinizadores: {
                    titulo: "Polinizadores de Chiapas",
                    especies: [
                        { nombre: "Abeja Real Melipona", cientifico: "Melipona solani", tipo: "Abeja nativa sin aguijón", rol: "Poliniza las flores de vainilla y las copas altas de la selva.", accent: "accent-yellow" },
                        { nombre: "Abeja Verde Brillante", cientifico: "Euglossa viridissima", tipo: "Abeja tornasol", rol: "Muy ágil; visita orquídeas y flores exóticas de la selva.", accent: "accent-green" },
                        { nombre: "Mariposa Alas de Cristal", cientifico: "Greta oto", tipo: "Mariposa transparente", rol: "Vuela bajo la sombra de la selva llevando polen entre las plantas.", accent: "accent-blue" },
                        { nombre: "Murciélago Frutero", cientifico: "Artibeus lituratus", tipo: "Mamífero nocturno", rol: "Come frutas por la noche, reparte semillas y poliniza árboles de la selva.", accent: "accent-purple" },
                        { nombre: "Abejorro de Montaña", cientifico: "Bombus wilmattae", tipo: "Abejorro de niebla", rol: "Trabaja en cafetales de altura donde hace frío y neblina.", accent: "accent-yellow" }
                    ]
                },
                flores: {
                    titulo: "Flores y plantas bajas",
                    beneficios: "Afianzan la tierra para que las lluvias fuertes no se lleven el suelo y dan néctar dulce.",
                    especies: [
                        { nombre: "Heliconia (Pico de Loro)", cientifico: "Heliconia psittacorum", funcion: "Flores rojas y naranjas con mucho néctar para colibríes y mariposas.", accent: "accent-orange" },
                        { nombre: "Salvia de Chiapas", cientifico: "Salvia chiapensis", funcion: "Flores color magenta que brotan casi todo el año y encantan a las abejas.", accent: "accent-purple" },
                        { nombre: "Orquídea Vainilla", cientifico: "Vanilla planifolia", funcion: "Planta trepadora que sube por los árboles y da vainas de vainilla.", accent: "accent-green" },
                        { nombre: "Begonia Silvestre", cientifico: "Begonia heracleifolia", funcion: "Crece al ras del suelo bajo la sombra y ayuda a guardar la humedad de la tierra.", accent: "accent-yellow" },
                        { nombre: "Platanillo / Achira", cientifico: "Canna indica", funcion: "Flores anaranjadas alegres y raíces gruesas que aflojan suelos pesados.", accent: "accent-orange" }
                    ]
                },
                dosel: {
                    titulo: "Árboles de sombra",
                    beneficios: "Refrescan el cultivo cuando el sol quema fuerte, mejoran la tierra y protegen al café y cacao.",
                    especies: [
                        { nombre: "Caoba", cientifico: "Swietenia macrophylla", funcion: "Árbol alto y majestuoso que protege las plantas de abajo y da refugio a aves.", accent: "accent-green" },
                        { nombre: "Madre de Cacao", cientifico: "Gliricidia sepium", funcion: "Abona la tierra con nutrientes naturales y da flores rosadas en primavera.", accent: "accent-yellow" },
                        { nombre: "Jinicuil", cientifico: "Inga jinicuil", funcion: "El árbol favorito para dar sombra al café; sus flores dan néctar dulce.", accent: "accent-green" },
                        { nombre: "Chicozapote", cientifico: "Manilkara zapota", funcion: "Árbol muy duradero que da frutos dulces y donde anidan abejas nativas.", accent: "accent-blue" }
                    ]
                },
                auxiliares: {
                    titulo: "Insectos que ayudan contra plagas",
                    beneficios: "Amigos naturales que cazan gusanos y plagas del cafetal sin meter veneno a la parcela.",
                    especies: [
                        { nombre: "Mantis Religiosa", cientifico: "Stagmomantis limbata", funcion: "Caza gusanos, orugas y bichos voladores que mastican las hojas.", accent: "accent-green" },
                        { nombre: "Avispa Cazadora", cientifico: "Polistes carnifex", funcion: "Controla orugas en la milpa y huertas de cacao.", accent: "accent-yellow" },
                        { nombre: "Chinche Cazadora", cientifico: "Zelus renardii", funcion: "Vigila las hojas y atrapa pequeños insectos que chupan la savia.", accent: "accent-orange" },
                        { nombre: "Araña Verde de Huerta", cientifico: "Peucetia viridans", funcion: "Vigila permanentemente las plantas atrapando plagas en sus telarañas.", accent: "accent-green" }
                    ]
                },
                infraestructura: {
                    titulo: "Agua, nidos y abono",
                    elementos: [
                        { nombre: "Cajas de madera para abejas", desc: "Colmenas rústicas de madera protegidas con techo de palma para que no les caiga la lluvia fuerte." },
                        { nombre: "Zanjas para absorber agua", desc: "Canales en la tierra con hojas secas para que el agua de lluvia penetre suavemente sin desgajar el suelo." },
                        { nombre: "Bebedero colgante con corchos", desc: "Recipiente colgado con corchos flotantes donde las abejas beben agua sin caerse." },
                        { nombre: "Composta de café y cacao", desc: "Montón donde se fermenta la cascarilla y restos de poda para convertirlos en abono orgánico." }
                    ]
                }
            }
        },
        "Guerrero": {
            modelSrc: "modelos/isla_guerrero.glb",
            infoCompleta: {
                titulo: "Isla de Cultivo – Guerrero",
                contexto: {
                    ubicacion: "Costa Grande, Tierra Caliente y Montaña de Guerrero, México",
                    climas: "Clima cálido con meses muy secos y calurosos durante el invierno y primavera.",
                    usosAgricolas: [
                        "Mango Ataulfo y Kent",
                        "Palma de coco",
                        "Ajonjolí",
                        "Flor de jamaica",
                        "Maíz y frijol de temporal",
                        "Maguey para mezcal"
                    ],
                    reto: "Aguantar varios meses continuos de secas, evitar quemas e incendios y frenar el deslave de tierra."
                },
                polinizadores: {
                    titulo: "Polinizadores de Guerrero",
                    especies: [
                        { nombre: "Murciélago Magueyero", cientifico: "Leptonycteris yerbabuenae", tipo: "Murciélago de flores", rol: "Muy especial; poliniza de noche las flores altas del maguey para que dé semilla.", accent: "accent-purple" },
                        { nombre: "Abeja Alfarera", cientifico: "Melipona fasciata", tipo: "Abeja nativa sin aguijón", rol: "Excelente para huertos de mango y flores de clima seco.", accent: "accent-yellow" },
                        { nombre: "Colibrí Berilo", cientifico: "Amazilia beryllina", tipo: "Picaflor resistente", rol: "Visita flores en barrancas secas y cercas vivas de nopal.", accent: "accent-green" },
                        { nombre: "Mariposa Malaquita", cientifico: "Siproeta stelenes", tipo: "Mariposa verde", rol: "Vuela entre huertos de fruta llevando polen en sus alas.", accent: "accent-blue" },
                        { nombre: "Abeja de Suelo", cientifico: "Andrena spp.", tipo: "Abeja de tierra", rol: "Hace nidos en la tierra seca y poliniza calabazas, sandías y frijoles.", accent: "accent-orange" }
                    ]
                },
                flores: {
                    titulo: "Flores y plantas bajas",
                    beneficios: "Aguantan calor de más de 40°C y sequía, regalando flores llenas de néctar cuando el monte está seco.",
                    especies: [
                        { nombre: "Flor de Jamaica", cientifico: "Hibiscus sabdariffa", funcion: "Da cálices rojos muy visitados por abejas y viste de verde el suelo seco.", accent: "accent-orange" },
                        { nombre: "Lantana (Tres Colores)", cientifico: "Lantana camara", funcion: "Florece todo el año con colores amarillo, rojo y naranja aun en tierra pedregosa.", accent: "accent-yellow" },
                        { nombre: "Cempasúchil Silvestre", cientifico: "Tagetes patula", funcion: "Aleja gusanos malos de las raíces y llama a muchas abejas silvestres.", accent: "accent-orange" },
                        { nombre: "Nopal de Verdura y Tuna", cientifico: "Opuntia ficus-indica", funcion: "Guarda agua viva en sus pencas; sus flores amarillas están repletas de polen.", accent: "accent-green" },
                        { nombre: "Zinnia Roja del Monte", cientifico: "Zinnia peruviana", funcion: "Planta silvestre muy aguantadora a la sequía, favorita de los colibríes.", accent: "accent-purple" }
                    ]
                },
                dosel: {
                    titulo: "Árboles de sombra",
                    beneficios: "Árboles fuertes que refrescan el terreno, tiran hojas secas para abonar el suelo y frenan el aire caliente.",
                    especies: [
                        { nombre: "Parota / Huanacaxtle", cientifico: "Enterolobium cyclocarpum", funcion: "Árbol gigante de copa ancha que baja la temperatura varios grados bajo su sombra.", accent: "accent-green" },
                        { nombre: "Guaje Rojo", cientifico: "Leucaena esculenta", funcion: "Tolera la aridez más fuerte, da vainas comestibles y abona la tierra.", accent: "accent-yellow" },
                        { nombre: "Cuajiote / Papelillo", cientifico: "Bursera fagaroides", funcion: "Árbol de corteza de papel; produce resina natural y da refugio a aves.", accent: "accent-blue" },
                        { nombre: "Ciruelo Silvestre", cientifico: "Spondias purpurea", funcion: "Florece justo antes de que inicien las lluvias, salvando a los enjambres en la época más seca.", accent: "accent-orange" }
                    ]
                },
                auxiliares: {
                    titulo: "Insectos que ayudan contra plagas",
                    beneficios: "Insectos carnívoros que limpian los huertos de mango y maguey sin dejar venenos en la cosecha.",
                    especies: [
                        { nombre: "Crisopa Parda", cientifico: "Hemerobius pacificus", funcion: "Se come pulgones y plagas durante los meses calurosos y secos.", accent: "accent-green" },
                        { nombre: "Mariquita Manchada", cientifico: "Coleomegilla maculata", funcion: "Ayuda a mantener sanos los sembradíos de jamaica, ajonjolí y maíz.", accent: "accent-orange" },
                        { nombre: "Escarabajo Tigre", cientifico: "Cicindela spp.", funcion: "Correveloz en el suelo cazando larvas dañinas y orugas.", accent: "accent-blue" },
                        { nombre: "Avispa Protectora del Maguey", cientifico: "Scutellista caerulea", funcion: "Evita que las cochinillas y plagas dañen las pencas del maguey.", accent: "accent-purple" }
                    ]
                },
                infraestructura: {
                    titulo: "Agua, nidos y abono",
                    elementos: [
                        { nombre: "Depósito de agua con fibra de coco", desc: "Pila de agua cubierta con fibra de coco para evitar que el sol evapore el agua con rapidez." },
                        { nombre: "Tubos de nido en la tierra", desc: "Tubos de barro enterrados donde las abejas de suelo pueden hacer su nido protegidas de pisadas." },
                        { nombre: "Cercas vivas de nopal y maguey", desc: "Hileras de magueyes y nopales que frenan el viento y evitan que la tierra se deslave en las lomas." },
                        { nombre: "Platos con piedras de río", desc: "Fuentes bajitas con piedritas donde el rocío de la mañana se junta y los insectos pueden beber." }
                    ]
                }
            }
        }
    };

    // ====================================================================================
    // RENDERIZADO DEL MOSAICO DINÁMICO
    // ====================================================================================
    function renderMosaic(regionName) {
        const regionObj = stateData[regionName];
        if (!regionObj) return;

        const info = regionObj.infoCompleta;

        // 1. Actualizar modelo 3D
        if (modelViewer && regionObj.modelSrc) {
            modelViewer.src = regionObj.modelSrc;
            if (modelFilenameTag) {
                modelFilenameTag.innerText = regionObj.modelSrc.split('/').pop();
            }
            if (viewerTitle) {
                viewerTitle.innerText = `Modelo 3D de la isla (${regionName})`;
            }
        }

        // 2. Actualizar encabezados
        if (headerRegionLabel) {
            headerRegionLabel.innerText = regionName;
        }

        // 3. Cultivos
        const cultivosContainer = document.getElementById('mosaic-cultivos');
        if (cultivosContainer) {
            cultivosContainer.innerHTML = `
                <div class="mosaic-title">
                    <h3>Cultivos de la zona</h3>
                </div>
                <p><strong>Ubicación:</strong> ${info.contexto.ubicacion}</p>
                <p style="margin-top: 0.3rem;"><strong>Clima:</strong> ${info.contexto.climas}</p>
                
                <h4 style="margin-top: 0.75rem; font-size: 0.9rem;">Cultivos presentes:</h4>
                <div class="tag-cloud">
                    ${info.contexto.usosAgricolas.map(c => `<span class="tag tag-highlight">${c}</span>`).join('')}
                </div>
                
                <div class="note-box">
                    <strong>Puntos de atención:</strong> ${info.contexto.reto}
                </div>
            `;
        }

        // 4. Polinizadores
        const polinizadoresContainer = document.getElementById('mosaic-polinizadores');
        if (polinizadoresContainer) {
            polinizadoresContainer.innerHTML = `
                <div class="mosaic-title">
                    <h3>Polinizadores</h3>
                </div>
                <p style="font-size: 0.85rem; margin-bottom: 0.5rem;">Especies que visitan y ayudan a polinizar en ${regionName}:</p>
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

        // 5. Flores y plantas bajas
        const floresContainer = document.getElementById('mosaic-flores');
        if (floresContainer) {
            floresContainer.innerHTML = `
                <div class="mosaic-title">
                    <h3>Flores y plantas bajas</h3>
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

        // 6. Árboles
        const arbolesContainer = document.getElementById('mosaic-arboles');
        if (arbolesContainer) {
            arbolesContainer.innerHTML = `
                <div class="mosaic-title">
                    <h3>Árboles de sombra</h3>
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

        // 7. Insectos benéficos
        const auxiliaresContainer = document.getElementById('mosaic-auxiliares');
        if (auxiliaresContainer) {
            auxiliaresContainer.innerHTML = `
                <div class="mosaic-title">
                    <h3>Insectos que ayudan contra plagas</h3>
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

        // 8. Instalaciones de apoyo
        const infraContainer = document.getElementById('mosaic-infraestructura');
        if (infraContainer) {
            infraContainer.innerHTML = `
                <div class="mosaic-title">
                    <h3>Agua, nidos y abono</h3>
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

    // ====================================================================================
    // EVENTOS DEL SELECTOR DE REGIONES
    // ====================================================================================
    const regionButtons = document.querySelectorAll('.region-btn');
    regionButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const region = btn.getAttribute('data-region');
            if (!region || !stateData[region]) return;

            regionButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            renderMosaic(region);
        });
    });

    // ====================================================================================
    // CONTROLES DEL VISOR 3D MODEL-VIEWER
    // ====================================================================================
    if (modelViewer) {
        // Monitoreo de progreso de descarga del modelo GLB (18 MB)
        modelViewer.addEventListener('progress', (e) => {
            const percent = (e.detail.totalProgress * 100).toFixed(0);
            if (progressFill) {
                progressFill.style.width = `${percent}%`;
            }
        });

        modelViewer.addEventListener('load', () => {
            if (progressFill) {
                progressFill.style.width = '100%';
                setTimeout(() => {
                    progressFill.style.width = '0%';
                }, 400);
            }
        });

        // Alternar auto-rotación
        if (btnToggleRotate) {
            btnToggleRotate.addEventListener('click', () => {
                if (modelViewer.hasAttribute('auto-rotate')) {
                    modelViewer.removeAttribute('auto-rotate');
                    btnToggleRotate.innerText = "Reanudar giro";
                } else {
                    modelViewer.setAttribute('auto-rotate', '');
                    btnToggleRotate.innerText = "Pausar giro";
                }
            });
        }

        // Restablecer cámara
        if (btnResetCamera) {
            btnResetCamera.addEventListener('click', () => {
                modelViewer.cameraOrbit = "0deg 75deg 105%";
                modelViewer.cameraTarget = "auto auto auto";
                modelViewer.fieldOfView = "auto";
            });
        }

        // Pantalla completa del 3D
        if (btnFullscreen3D && viewerWrapper) {
            btnFullscreen3D.addEventListener('click', () => {
                if (!document.fullscreenElement) {
                    viewerWrapper.requestFullscreen?.().catch(err => {
                        console.warn("Fullscreen request error:", err);
                    });
                } else {
                    document.exitFullscreen?.();
                }
            });
        }
    }

    // Inicializar por defecto con Oaxaca
    renderMosaic("Oaxaca");
});