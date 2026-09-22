import re
from datetime import datetime
from config import COLUMN_ALIASES, SUBITEM_COLUMNS

IMMUTABLE_POINTS = [
    "CAMBIO DE PROVEEDOR: Si el proveedor no reacciona a los requerimientos solicitados previos y a los contratados, se debe cambiar no más de 3 días después de la falta de reacción.",
    "GARANTÍA: Si el proveedor tuvo un trabajo de mala calidad, se deben descontar materiales y otros gastos que se requieran.",
    "RETENCIÓN: 5% del monto total retenido por 3 meses luego de haber recibido con satisfacción los trabajos.",
    "El proveedor se compromete a cumplir con todas las normas del ACUERDO GUBERNATIVO 229-204 Y SUS REFORMAS 33-2016. De no cumplir con las normativas del acuerdo o las internas del proyecto, se podrá dar por terminado el contrato.",
]

# Fallback amounts, taken from the original template (cells P30-P33) - used
# only if the multa is selected but the Lider left its monto field blank.
# "atraso" isn't here - it's resolved separately by build_multas(), from
# its own fixed-choice dropdown rather than a free-typed number.
MULTAS_DEFAULTS = {
    "orden": "Q.25 POR EVENTO",
    "seguridad": "Q.50 POR PERSONA",
    "reporteria": "Q.25 POR EVENTO",
}

# The Lider only types a plain number in each "Multa por ..." field; this
# formats it with the unit that multa actually uses in the template.
MULTAS_FORMAT = {
    "orden": "Q.{monto} POR EVENTO",
    "seguridad": "Q.{monto} POR PERSONA",
    "reporteria": "Q.{monto} POR EVENTO",
}

# Field name (from COLUMN_ALIASES) holding that typed number, per multa.
MULTAS_MONTO_FIELDS = {
    "orden": "multa_orden_monto",
    "seguridad": "multa_seguridad_monto",
    "reporteria": "multa_reporteria_monto",
}

# Maps each "Multas a Aplicar" dropdown option label (lowercase) to the
# multa key it selects. Matches the exact option text configured in Monday
# (multi_select278mnjmn), accents included, plus a couple of forgiving
# fallback variants. "Por atraso de entrega" was removed from this
# checkbox list - atraso now has its own dropdown, resolved separately.
MULTAS_OPTION_MAP = {
    "por órden y limpieza": "orden",
    "por orden y limpieza": "orden",
    "orden y limpieza": "orden",
    "orden": "orden",
    "por no cumplir con seguridad industrial": "seguridad",
    "seguridad industrial": "seguridad",
    "seguridad": "seguridad",
    "por no cumplir con documentos de reportería semanal": "reporteria",
    "por no cumplir con documentos de reporteria semanal": "reporteria",
    "reportería semanal": "reporteria",
    "reporteria semanal": "reporteria",
    "reporteria": "reporteria",
}

# Cada opción del multi-select del formulario (más simple, para el Líder)
# se expande a una o más líneas exactas de "Puntos de Revisión Específica"
# tomadas de la plantilla oficial de ese rubro - así el documento final
# siempre usa el texto oficial, nunca el texto corto de la opción. Solo
# cubre los rubros cuya plantilla oficial (100-117) ya se revisó línea por
# línea; los demás rubros siguen usando el texto de la opción tal cual
# (comportamiento anterior) hasta que se agregue su plantilla oficial.
PUNTOS_OPCION_MAP = {
    "herreria": {
        "soldaduras completas": [
            "Soldaduras y uniones estructurales revisadas",
        ],
        "soldaduras limpias": [
            "Limpieza final realizada, sin residuos metálicos",
        ],
        "cordones uniformes": [
            "Material utilizado según especificaciones",
            "Bordes sin filos peligrosos",
        ],
        "aplicación de anticorrosivo": [
            "Tratamientos anticorrosivos aplicados (galvanizado, pintura)",
        ],
        "aplicacion de anticorrosivo": [
            "Tratamientos anticorrosivos aplicados (galvanizado, pintura)",
        ],
        "aplicación de pintura final": [
            "Acabados bien ejecutados (lijado, pulido, pintura)",
            "Pintura o esmalte aplicado correctamente",
            "Estado final documentado y registrado",
        ],
        "aplicacion de pintura final": [
            "Acabados bien ejecutados (lijado, pulido, pintura)",
            "Pintura o esmalte aplicado correctamente",
            "Estado final documentado y registrado",
        ],
        "anclajes correctos": [
            "Mecanismos móviles funcionales (bisagras, cerraduras, ruedas)",
            "Fijaciones y anclajes seguros",
            "Pruebas de carga exitosas en elementos críticos",
            "Tornillos y remaches de seguridad instalados correctamente",
        ],
        "nivelación": [
            "Barandales y puertas nivelados y aplomados",
            "Drenaje funcional en piezas expuestas",
        ],
        "nivelacion": [
            "Barandales y puertas nivelados y aplomados",
            "Drenaje funcional en piezas expuestas",
        ],
        "plomeo": [
            "Barandales y puertas nivelados y aplomados",
        ],
        "alineación": [
            "Dimensiones y alineación conforme a planos",
            "Buena integración con otros elementos estructurales",
        ],
        "alineacion": [
            "Dimensiones y alineación conforme a planos",
            "Buena integración con otros elementos estructurales",
        ],
    },
    "ventaneria": {
        "nivelación": ["Marcos nivelados y plomados correctamente"],
        "nivelacion": ["Marcos nivelados y plomados correctamente"],
        "plomeo": ["Marcos nivelados y plomados correctamente"],
        "sellos de silicón": [
            "Burletes y sellado perimetral instalados correctamente",
        ],
        "sellos de silicon": [
            "Burletes y sellado perimetral instalados correctamente",
        ],
        "vidrios sin daños": [
            "Vidrios instalados sin daños, rayones ni burbujas",
        ],
        "vidrios sin danos": [
            "Vidrios instalados sin daños, rayones ni burbujas",
        ],
        "anclajes correctos": [
            "Fijación y anclaje realizados al soporte estructural",
            "Medidas instaladas conforme a lo cotizado",
        ],
        "limpieza final": [
            "Instalación limpia, sin residuos de sellador ni adhesivos",
        ],
        "funcionamiento de hojas móviles": [
            "Mecanismos de apertura y cierre funcionando correctamente",
        ],
        "funcionamiento de hojas moviles": [
            "Mecanismos de apertura y cierre funcionando correctamente",
        ],
        "acabados completos": [
            "Material instalado concuerda con lo cotizado",
            "Herrajes y accesorios colocados según especificación",
            "Alineación correcta con otras ventanas del proyecto",
            "Integración adecuada con acabados contiguos (pintura, yeso)",
            "Perfiles sin deformaciones visibles por instalación",
        ],
    },
    "tabla_yeso": {
        "nivelación": [
            "Paneles alineados y nivelados según diseño",
            "Nivelación verificada con láser en grandes superficies",
        ],
        "nivelacion": [
            "Paneles alineados y nivelados según diseño",
            "Nivelación verificada con láser en grandes superficies",
        ],
        "plomeo": [
            "Estructura soporte instalada correctamente (montantes y canales)",
            "Fijaciones realizadas con separación y cantidad adecuada",
            "Resistencia estructural del panel comprobada",
            "Paneles en techos suspendidos presentan estabilidad",
        ],
        "uniones tratadas": [
            "Juntas tratadas con cinta y masilla en todas las uniones",
            "Insonorización adecuada en paredes divisorias",
        ],
        "juntas lijadas": [
            "Cortes limpios realizados en esquinas, puertas y ventanas",
        ],
        "acabado uniforme": [
            "Materiales empleados cumplen con especificaciones de proyecto",
            "Integración adecuada con molduras, pisos y otros acabados",
        ],
        "ausencia de grietas": [
            "Refuerzos colocados en puntos críticos según requerimientos",
        ],
        "pintura completa": [
            "Acabado superficial sin fisuras ni imperfecciones",
        ],
        "limpieza final": [
            "Limpieza completa de polvo y residuos previo a acabado final",
        ],
    },
    "pintura": {
        "cobertura uniforme": [
            "Aplicación uniforme y con buen acabado",
            "Compatibilidad entre diferentes pinturas comprobada",
        ],
        "color correcto": [
            "Tipo y color de pintura aplicados según especificaciones",
        ],
        "sin manchas": [
            "Superficie sin escurrimientos, burbujas ni manchas",
        ],
        "sin escurrimientos": [
            "Superficie sin escurrimientos, burbujas ni manchas",
        ],
        "preparación adecuada de superficie": [
            "Adherencia comprobada satisfactoriamente",
            "Imprimantes y selladores aplicados correctamente",
            "Compatibilidad de pintura con material base verificada",
        ],
        "preparacion adecuada de superficie": [
            "Adherencia comprobada satisfactoriamente",
            "Imprimantes y selladores aplicados correctamente",
            "Compatibilidad de pintura con material base verificada",
        ],
        "acabado final aprobado": [
            "Esquinas, uniones y bordes bien detallados",
            "Textura y acabado final conforme a lo especificado (mate, satinado, brillante)",
            "Retoques realizados tras instalación de otros elementos",
        ],
        "limpieza final": [
            "Zonas no deseadas libres de residuos de pintura",
        ],
    },
    "electricidad": {
        "pruebas de funcionamiento": [
            "Continuidad y resistencia eléctrica verificadas",
            "Pruebas de carga y amperaje realizadas con éxito",
            "Luminarias instaladas y funcionando correctamente",
            "Conductores con aislamiento verificado en pruebas de resistencia",
            "Iluminación de emergencia funcional y conforme a diseño",
        ],
        "canalización correcta": [
            "Instalación realizada según planos eléctricos y normativa",
            "Canalizaciones y cajas ubicadas conforme a diseño",
            "Bandejas y canalizaciones correctamente fijadas",
            "Ductos eléctricos con integridad estructural confirmada",
        ],
        "canalizacion correcta": [
            "Instalación realizada según planos eléctricos y normativa",
            "Canalizaciones y cajas ubicadas conforme a diseño",
            "Bandejas y canalizaciones correctamente fijadas",
            "Ductos eléctricos con integridad estructural confirmada",
        ],
        "etiquetado de circuitos": [
            "Circuitos eléctricos rotulados y documentados correctamente",
        ],
        "conexiones seguras": [
            "Cableado instalado con el calibre y tipo especificado",
            "Conexiones y empalmes revisados en tableros y cajas",
            "Compatibilidad entre conductores y térmicos verificada",
            "Fases correctamente conectadas en sistemas trifásicos",
        ],
        "tableros identificados": [
            "Interruptores diferenciales presentes en tableros",
            "Protecciones contra sobretensiones instalad",
            "Dispositivos de control energético instalados correctamente",
        ],
        "voltajes correctos": [
            "Polaridad verificada en tomacorrientes y conexiones",
            "Caída de tensión dentro de rangos aceptables",
        ],
        "puesta a tierra": [
            "Puesta a tierra instalada en equipos y tableros",
        ],
        # "Limpieza final" no tiene una línea correspondiente en la
        # plantilla oficial de Electricidad (ningún punto menciona
        # limpieza) - se deja sin mapear a propósito, en vez de forzar
        # una coincidencia que no aplica.
        "limpieza final": [],
    },
    "cortinas_metalicas": {
        "medidas y ajuste correcto": ["Medidas y ajuste correcto en el vano"],
        "funcionamiento de apertura/cierre": [
            "Estructura y mecanismo de apertura/cierre funcional",
            "Maniobra manual y automática probada exitosamente",
            "Operación con nivel de ruido aceptable",
        ],
        "motor y controles": [
            "Motor y controles verificados (si aplica)",
            "Cables y conexiones eléctricas en buen estado (si aplica)",
            "Controles remotos o sistemas de activación operativos (si aplica)",
        ],
        "guías rieles y poleas": [
            "Guías y rieles sin obstrucciones",
            "Poleas y ejes sin desgaste",
        ],
        "anclajes correctos": ["Fijaciones y anclajes firmes y seguros"],
        "seguridad operativa": [
            "Elementos de seguridad revisados y operativos (freno, bloqueo)",
            "Frenos electromagnéticos ajustados correctamente (si aplica)",
        ],
        "lubricación y ajuste": [
            "Mecanismos móviles lubricados",
            "Balanceo y tensión de resortes ajustados",
        ],
        "lubricacion y ajuste": [
            "Mecanismos móviles lubricados",
            "Balanceo y tensión de resortes ajustados",
        ],
        "limpieza final": ["Área limpia, sin residuos de instalación"],
        "sellos y sensores": [
            "Sellos y burletes en buen estado (si aplica)",
            "Sensores y fotoceldas funcionales (si aplica)",
        ],
        "acabado sin daños": ["Láminas sin corrosión ni daños visibles"],
        "acabado sin danos": ["Láminas sin corrosión ni daños visibles"],
    },
    "enlaminado": {
        "alineación y nivelación": [
            "Alineación y fijación adecuadas",
            "Superficie nivelada y plana",
        ],
        "alineacion y nivelacion": [
            "Alineación y fijación adecuadas",
            "Superficie nivelada y plana",
        ],
        "solapes y sellados": [
            "Solapes y sellados correctamente ejecutados",
            "Juntas y uniones con buena hermeticidad",
        ],
        "acabado sin daños": [
            "Recubrimientos y acabados en buen estado",
            "Sin daños mecánicos ni deformaciones",
            "Bordes y cortes seguros, sin desprendimientos",
        ],
        "acabado sin danos": [
            "Recubrimientos y acabados en buen estado",
            "Sin daños mecánicos ni deformaciones",
            "Bordes y cortes seguros, sin desprendimientos",
        ],
        "material según especificación": ["Láminas del calibre y tipo especificado"],
        "material segun especificacion": ["Láminas del calibre y tipo especificado"],
        "fijaciones correctas": [
            "Fijaciones correctamente colocadas y ajustadas",
            "Sistemas de fijación correctamente instalados",
            "Buena adherencia y compatibilidad con la estructura base",
        ],
        "drenaje funcional": ["Drenaje funcional con pendiente adecuada"],
        "anticorrosivo aplicado": ["Protección anticorrosiva aplicada en uniones (si aplica)"],
        "limpieza final": ["Área limpia y sin residuos metálicos"],
    },
    "canal_flashing": {
        "instalación correcta de canaletas": [
            "Canaletas y bajantes instalados correctamente",
            "Bajantes sin obstrucciones visibles",
        ],
        "instalacion correcta de canaletas": [
            "Canaletas y bajantes instalados correctamente",
            "Bajantes sin obstrucciones visibles",
        ],
        "pendientes para drenaje": ["Pendientes adecuadas para buen flujo de agua"],
        "sellados sin filtraciones": [
            "Uniones y sellados sin filtraciones",
            "Tornillería y uniones correctamente selladas",
        ],
        "anclajes y fijaciones": [
            "Fijaciones y anclajes seguros",
            "Anclajes y soportes firmemente instalados",
        ],
        "material según especificación": ["Material y calibre conforme a especificaciones"],
        "material segun especificacion": ["Material y calibre conforme a especificaciones"],
        "solapes correctos": ["Solapes y traslapes ejecutados correctamente"],
        "acabado sin daños": ["Sin deformaciones ni daños en instalación"],
        "acabado sin danos": ["Sin deformaciones ni daños en instalación"],
        "limpieza final": ["Libre de residuos o acumulaciones"],
    },
    "acm": {
        "medidas y cortes precisos": ["Dimensiones y cortes precisos verificados"],
        "nivelación y alineación": ["Paneles alineados y nivelados correctamente"],
        "nivelacion y alineacion": ["Paneles alineados y nivelados correctamente"],
        "anclajes correctos": ["Sistemas de fijación y anclajes seguros"],
        "uniones y sellados": [
            "Uniones y sellados entre paneles correctamente ejecutados",
            "Bordes y uniones sin deformaciones",
        ],
        "acabado sin daños": [
            "Superficies sin rayones, golpes ni deformaciones",
            "Acabado final conforme a diseño (mate o brillante)",
        ],
        "acabado sin danos": [
            "Superficies sin rayones, golpes ni deformaciones",
            "Acabado final conforme a diseño (mate o brillante)",
        ],
        "ventilación y dilatación": ["Ventilación y dilatación adecuadas instaladas"],
        "ventilacion y dilatacion": ["Ventilación y dilatación adecuadas instaladas"],
        "limpieza final": ["Zona de instalación limpia, sin residuos"],
        "accesibilidad para mantenimiento": ["Accesibilidad futura para mantenimiento asegurada"],
    },
    "alquiler_grua": {
        "documentación del operador": ["Documentación y certificación del operador verificadas"],
        "documentacion del operador": ["Documentación y certificación del operador verificadas"],
        "mantenimiento vigente": ["Mantenimiento vigente de grúa dentro de los últimos 3 meses"],
        "seguros actualizados": ["Seguros actualizados del equipo y operador comprobados"],
        "revisión física y mecánica del equipo": [
            "Revisión del estado físico y mecánico de la grúa completado: i. Grúa limpia y sin residuos comprometedores ii. Carga máxima y distribución de peso verificados iii. Contrapesos y estabilizadores en buen estado iv. Neumáticos y chasis inspeccionados v. Sistema hidráulico sin fugas vi. Elementos de izaje en óptimas condiciones vii. Iluminación funcional para trabajos nocturnos",
        ],
        "revision fisica y mecanica del equipo": [
            "Revisión del estado físico y mecánico de la grúa completado: i. Grúa limpia y sin residuos comprometedores ii. Carga máxima y distribución de peso verificados iii. Contrapesos y estabilizadores en buen estado iv. Neumáticos y chasis inspeccionados v. Sistema hidráulico sin fugas vi. Elementos de izaje en óptimas condiciones vii. Iluminación funcional para trabajos nocturnos",
        ],
        "pruebas de maniobras": [
            "Pruebas previas a maniobras completadas: i. Controles de mando y respuesta verificados ii. Frenos y sistemas de seguridad funcionales",
        ],
        "seguridad industrial": [
            "Autorización de Seguridad Industrial otorgada: i. Uso correcto de equipo de protección ii. Área de trabajo debidamente señalizada y delimitada iii. Método de comunicación operador–tierra definida iv. Lista de cumplimiento firmada y entregada",
        ],
        "condiciones climáticas seguras": ["Operación realizada bajo condiciones climáticas seguras"],
        "condiciones climaticas seguras": ["Operación realizada bajo condiciones climáticas seguras"],
    },
    "bomba_concreto": {
        "bomba en buen estado": [
            "Bomba inspeccionada y con mantenimiento vigente",
            "Mangueras y conexiones sin fugas ni desgaste",
        ],
        "capacidad conforme a requerimiento": ["Capacidad de bombeo conforme a los requerimientos"],
        "pruebas de funcionamiento": ["Pruebas de funcionamiento satisfactorias"],
        "concreto según especificación": ["Concreto entregado conforme a especificaciones técnicas"],
        "concreto segun especificacion": ["Concreto entregado conforme a especificaciones técnicas"],
        "nivelación y distribución": [
            "Nivelación y distribución del concreto correctamente ejecutadas",
            "Juntas de dilatación y construcción instaladas",
        ],
        "nivelacion y distribucion": [
            "Nivelación y distribución del concreto correctamente ejecutadas",
            "Juntas de dilatación y construcción instaladas",
        ],
        "acabado final aprobado": ["Acabado final del concreto cumple con calidad requerida"],
        "limpieza final": ["Limpieza de equipo y área de trabajo realizada"],
        "anticipación de instalación": [
            "Equipo instalado con al menos 1 hora de anticipación de instalación de tuberías",
        ],
        "anticipacion de instalacion": [
            "Equipo instalado con al menos 1 hora de anticipación de instalación de tuberías",
        ],
    },
    "puertas_madera": {
        "medidas y ajuste en marco": [
            "Medidas y ajuste en marco confirmados según planos.",
            "Holguras y separación con el marco dentro de tolerancias aceptables.",
        ],
        "herrajes funcionando": [
            "Bisagras, cerraduras y herrajes correctamente instalados y funcionales.",
        ],
        "acabado y barniz": [
            "Acabado superficial y barniz aplicados sin imperfecciones ni manchas.",
            "Estética y uniformidad del color según diseño aprobado.",
        ],
        "funcionamiento y alineación": [
            "Funcionamiento correcto y alineación de la hoja respecto al marco.",
            "Cierre suave y ajuste en marcos verificado.",
        ],
        "funcionamiento y alineacion": [
            "Funcionamiento correcto y alineación de la hoja respecto al marco.",
            "Cierre suave y ajuste en marcos verificado.",
        ],
        "sellado perimetral": [
            "Sellado perimetral instalado y funcional contra ruidos y filtraciones.",
        ],
        "anclajes y estabilidad": [
            "Fijaciones y anclajes estables, especialmente en puertas pesadas.",
            "Puerta presenta estabilidad estructural adecuada.",
        ],
        "limpieza final": ["Limpieza final realizada y sin residuos de instalación."],
        "sin deformaciones": ["Sin deformaciones visibles por humedad o temperatura."],
    },
    "elevadores": {
        "instalación según normativa": ["Instalación ejecutada conforme a planos y normativa aplicable."],
        "instalacion segun normativa": ["Instalación ejecutada conforme a planos y normativa aplicable."],
        "pruebas de funcionamiento con carga": [
            "Pruebas de funcionamiento satisfactorias en todos los niveles y con carga máxima.",
            "Arranque y frenado con carga sin anomalías.",
            "Tiempos de respuesta y velocidad adecuados según especificación.",
        ],
        "acabados de cabina": [
            "Acabados en cabina y accesos sin defectos.",
            "Iluminación interior y exterior operativa.",
            "Cabina con ventilación funcional y temperatura controlada.",
        ],
        "sistemas de emergencia y seguridad": [
            "Sistemas de emergencia y alarmas operativos.",
            "Puertas y sensores de seguridad operativos.",
            "Protección contra sobrecargas eléctricas instalada.",
        ],
        "nivelación por piso": ["Nivelación precisa en cada piso sin desniveles."],
        "nivelacion por piso": ["Nivelación precisa en cada piso sin desniveles."],
        "cables y poleas de tracción": [
            "Cables, poleas y sistemas de tracción inspeccionados y sin fallas.",
            "Rieles y guías inspeccionadas, sin obstrucciones ni defectos.",
        ],
        "cables y poleas de traccion": [
            "Cables, poleas y sistemas de tracción inspeccionados y sin fallas.",
            "Rieles y guías inspeccionadas, sin obstrucciones ni defectos.",
        ],
        "botoneras y señalización": ["Botoneras y señalización instaladas y funcionales."],
        "botoneras y senalizacion": ["Botoneras y señalización instaladas y funcionales."],
        "documentación técnica": [
            "Documentación técnica y certificaciones entregadas.",
            "Protocolos de mantenimiento disponibles y acordes al equipo.",
            "Bitácora de pruebas operativas completada y archivada",
        ],
        "documentacion tecnica": [
            "Documentación técnica y certificaciones entregadas.",
            "Protocolos de mantenimiento disponibles y acordes al equipo.",
            "Bitácora de pruebas operativas completada y archivada",
        ],
        "eficiencia y confort": [
            "Consumo energético dentro de parámetros eficientes.",
            "Ruido y vibraciones en operación dentro de rangos normales.",
        ],
        "acceso para mantenimiento": ["Acceso a componentes para mantenimiento sin restricciones."],
    },
    "pozo_mecanico": {
        "dimensiones según planos": ["Profundidad y diámetro del pozo conforme a planos aprobados."],
        "dimensiones segun planos": ["Profundidad y diámetro del pozo conforme a planos aprobados."],
        "entubado y sellos": [
            "Entubado y sellados adecuados garantizan integridad del pozo.",
            "Sellos contra contaminación externa instalados y verificados.",
            "Sellado superior del pozo instalado correctamente.",
        ],
        "pruebas de caudal y bombeo": [
            "Pruebas de caudal y flujo realizadas satisfactoriamente.",
            "Pruebas de bombeo realizadas si aplica, con parámetros dentro de norma.",
        ],
        "estabilidad de paredes": ["Paredes estables y revestimiento sin colapsos ni desplazamientos."],
        "drenaje funcional": ["Sistema de drenaje funcional y evacuación de agua efectiva."],
        "documentación técnica": [
            "Documentación técnica y certificación de obra entregada.",
            "Materiales de perforación verificados según especificaciones.",
        ],
        "documentacion tecnica": [
            "Documentación técnica y certificación de obra entregada.",
            "Materiales de perforación verificados según especificaciones.",
        ],
        "calidad del agua": [
            "Calidad del agua extraída evaluada cuando corresponde.",
            "Flujo de agua libre de sedimentos y partículas.",
            "Sistema de filtración eficiente y en funcionamiento.",
        ],
    },
    "pilotes_nailing": {
        "ubicación y profundidad según planos": [
            "Ubicación y profundidad de pilotes verificadas según planos estructurales.",
            "Pilotes verticales y alineados según especificaciones.",
        ],
        "ubicacion y profundidad segun planos": [
            "Ubicación y profundidad de pilotes verificadas según planos estructurales.",
            "Pilotes verticales y alineados según especificaciones.",
        ],
        "refuerzo y concreto": [
            "Refuerzo y concreto correctamente instalados en cada pilote.",
            "Concreto utilizado cumple estándares de calidad establecidos.",
            "Recubrimiento de acero de refuerzo conforme a diseño.",
        ],
        "estabilidad de taludes y drenaje": [
            "Taludes estables y drenaje operativo en el área intervenida.",
            "Sistema de contención sin filtraciones ni humedad.",
        ],
        "anclajes y tensores": [
            "Tensores y anclajes de sistema de contención correctamente instalados.",
            "Anclajes activos tensados y supervisados en pre y post.",
        ],
        "sin fisuras ni desplazamientos": [
            "Pilotes sin fisuras ni desplazamientos tras fundición.",
            "Sin asentamientos diferenciales en zona estructural.",
        ],
        "contacto con subestructura": [
            "Contacto adecuado entre cimentación y subestructura verificado.",
            "Uniones entre pilotes y estructura superior selladas.",
        ],
        "compactación y limpieza": [
            "Suelo circundante compactado adecuadamente.",
            "Proceso de perforación ejecutado con limpieza de escombros.",
        ],
        "compactacion y limpieza": [
            "Suelo circundante compactado adecuadamente.",
            "Proceso de perforación ejecutado con limpieza de escombros.",
        ],
    },
    "acabados": {
        "color correcto": ["Textura y tonalidad uniformes en toda la superficie"],
        "textura uniforme": ["Textura y tonalidad uniformes en toda la superficie"],
        "acabado limpio": [
            "Superficie limpia y debidamente protegida",
            "Bordes y esquinas bien definidos",
        ],
        "sin daños visibles": [
            "Superficie sin fisuras, grietas ni defectos visibles",
            "Sin eflorescencias ni manchas visibles",
        ],
        "sin danos visibles": [
            "Superficie sin fisuras, grietas ni defectos visibles",
            "Sin eflorescencias ni manchas visibles",
        ],
        "conforme a muestras aprobadas": [
            "Nivelación y espesores verificados según especificaciones",
            "Buena adherencia del acabado sobre la base comprobada",
            "Juntas de dilatación correctamente aplicadas",
            "Curado adecuado realizado para evitar contracción",
            "Impermeabilización aplicada en zonas húmedas",
            "Selladores correctamente aplicados",
        ],
        "limpieza final": ["Registro fotográfico del estado final completo"],
    },
    "impermeabilizacion": {
        "superficie preparada": [
            "Adherencia adecuada en esquinas y juntas críticas.",
            "Refuerzos correctamente colocados en puntos de mayor desgaste.",
        ],
        "aplicación completa": ["Aplicación uniforme verificada en toda la superficie."],
        "aplicacion completa": ["Aplicación uniforme verificada en toda la superficie."],
        "espesor uniforme": [
            "Espesor de la capa impermeabilizante cumple con especificaciones del sistema aplicado.",
        ],
        "prueba de estanqueidad": [
            "No se evidencian grietas, burbujas ni desprendimientos en la capa impermeabilizante.",
            "Material expuesto al clima mantiene sus propiedades sin deterioro visible.",
            "Sellos en bordes y uniones sin signos de desgaste ni separación.",
        ],
        "ausencia de filtraciones": ["No se presentan filtraciones de agua en las áreas tratadas."],
        # "Limpieza final" no tiene una linea correspondiente en la plantilla
        # oficial de Impermeabilizantes - mismo caso que Electricidad, se
        # deja sin mapear a proposito.
        "limpieza final": [],
    },
}


def _values(item):
    """Extract column values from an item as a dictionary."""
    return {
        c["id"]: (c.get("text") or "").strip()
        for c in item.get("column_values", [])
    }


def _pick(values, key):
    """Pick the first available column value for a given key from COLUMN_ALIASES."""
    if key not in COLUMN_ALIASES:
        return ""

    for column_id in COLUMN_ALIASES[key]:
        if values.get(column_id):
            return values[column_id]

    return ""


def item_data(item):
    """Extract and organize item data using column aliases."""
    v = _values(item)

    data = {
        k: _pick(v, k)
        for k in COLUMN_ALIASES
    }

    data["item_id"] = str(item["id"])
    data["item_name"] = item.get("name", "")
    data["board_id"] = str(
        item.get("board", {}).get("id", "")
    )
    data["subitems"] = item.get("subitems", [])

    return data


def split_lines(text):
    """Split text into lines, removing empty ones and normalizing whitespace."""
    return [
        " ".join(x.split())
        for x in (text or "").splitlines()
        if x.strip()
    ]


def numbered(lines):
    """Convert a list of lines into a numbered list format."""
    return "\n".join(
        f"{i}. {x}"
        for i, x in enumerate(lines, 1)
    )


def pct(value):
    """Ensure a value ends with a percentage symbol."""
    value = (value or "").strip()

    return (
        value
        if not value
        or value.endswith("%")
        else value + "%"
    )


def display_date(value):
    """Convert a date string to DD/MM/YYYY format, supporting multiple input formats."""
    if not value:
        return ""

    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(
                value,
                fmt
            ).strftime("%d/%m/%Y")
        except ValueError:
            pass

    return value


def rubric_code(rubro):
    """Extract the rubric code (1XX pattern) from a rubric string."""

    m = re.search(
        r"\b(1\d{2})\b",
        rubro or ""
    )

    return m.group(1) if m else "100"


def build_programacion(subitems):
    """Build a list of programming entries from subitems with dates and observations."""
    rows = []

    for s in subitems:

        v = {
            c["id"]: (
                c.get("text") or ""
            ).strip()
            for c in s.get(
                "column_values",
                []
            )
        }

        area = (
            s.get("name") or ""
        ).strip()

        ini = display_date(
            v.get(
                SUBITEM_COLUMNS["fecha_inicio"],
                ""
            )
        )

        fin = display_date(
            v.get(
                SUBITEM_COLUMNS["fecha_fin"],
                ""
            )
        )

        obs = v.get(
            SUBITEM_COLUMNS["observaciones"],
            ""
        )

        if any((area, ini, fin, obs)):

            rows.append({
                "area": area,
                "inicio": ini,
                "fin": fin,
                "obs": obs,
            })

    return rows


def build_services(data):
    """Build a list of basic services from comma/semicolon-separated values."""
    values = [
        x.strip()
        for x in (
            data.get(
                "servicios_basicos"
            )
            or ""
        ).replace(
            ";",
            ","
        ).split(",")
        if x.strip()
        and x.strip().lower() != "otros"
    ]

    other = (
        data.get(
            "otro_servicio_basico",
            ""
        )
        .strip()
    )

    if (
        other
        and other.lower()
        not in {
            x.lower()
            for x in values
        }
    ):
        values.append(other)

    return values


def build_planos_entregados(data):

    selected = parse_multi(
        data.get("planos_entregados")
    )

    return {
        "arquitectura": "SI" if "arquitectura" in selected else "NO",
        "cotas": "SI" if "cotas" in selected else "NO",
        "elevaciones": "SI" if "elevaciones y secciones" in selected else "NO",
        "hidrosanitarias": "SI" if "hidrosanitarias" in selected else "NO",
        "electricidad": "SI" if "electricidad" in selected else "NO",
        "acabados": "SI" if "acabados" in selected else "NO",
        "estructura_principal": "SI" if "estructura principal" in selected else "NO",
        "estructura_secundaria": "SI" if "estructura secundaria" in selected else "NO",
        "obras_secundarias": "SI" if "obras secundarias" in selected else "NO",
    }


def build_planos(data):

    selected = parse_multi(
        data.get("planos_entregados")
    )

    return {
        "{{PL_ARQ}}":
            "SI" if "arquitectura" in selected else "NO",

        "{{PL_COTAS}}":
            "SI" if "cotas" in selected else "NO",

        "{{PL_ELEV}}":
            "SI" if "elevaciones y secciones" in selected else "NO",

        "{{PL_HIDRO}}":
            "SI" if "hidrosanitarias" in selected else "NO",

        "{{PL_ELEC}}":
            "SI" if "electricidad" in selected else "NO",

        "{{PL_ACAB}}":
            "SI" if "acabados" in selected else "NO",

        "{{PL_ESTR_PRIN}}":
            "SI" if "estructura principal" in selected else "NO",

        "{{PL_ESTR_SEC}}":
            "SI" if "estructura secundaria" in selected else "NO",

        "{{PL_OBRAS}}":
            "SI" if "obras secundarias" in selected else "NO",
    }


def build_template_points(data):

    plantilla = (
        data.get("plantilla") or ""
    ).strip().lower()

    mapping = {
        "herrería": "herreria",
        "ventanería": "ventaneria",
        "tabla yeso": "tabla_yeso",
        "pintura": "pintura",
        "electricidad": "electricidad",
        "piso": "piso",
        "cielo falso": "cielo_falso",
        "aluminio y vidrio": "aluminio_vidrio",
        "hidrosanitaria": "hidrosanitaria",
        "aire acondicionado": "aac",
        "sistema contra incendios": "sci",
        "carpintería": "carpinteria",
        "mobiliario": "mobiliario",
        "mampostería": "mamposteria",
        "obra civil": "obra_civil",
        "topografía": "topografia",
        "urbanización": "urbanizacion",
        "cubierta": "cubierta",
        "impermeabilización": "impermeabilizacion",
        "estructura metálica": "estructura_metalica",
        "señalización": "senalizacion",
        "acabados": "acabados",
        "cortinas metálicas": "cortinas_metalicas",
        "enlaminado": "enlaminado",
        "canal y flashing": "canal_flashing",
        "acm": "acm",
        "alquiler de grúa + operador": "alquiler_grua",
        "bomba y colocación de concreto": "bomba_concreto",
        "puertas de madera": "puertas_madera",
        "elevadores": "elevadores",
        "pozo mecánico": "pozo_mecanico",
        "pilotes + nailing": "pilotes_nailing",
    }

    field = mapping.get(plantilla)

    if not field:
        return []

    values = data.get(field) or ""

    selected_options = [
        x.strip()
        for x in values.split(",")
        if x.strip()
        and x.strip().lower() != "otros"
    ]

    option_map = PUNTOS_OPCION_MAP.get(field)

    if option_map:
        # El texto oficial de la plantilla, expandido desde cada opción
        # elegida (una opción puede cubrir una o varias líneas) -
        # deduplicado por si dos opciones comparten la misma línea.
        points = []
        seen = set()

        for option in selected_options:
            for line in option_map.get(option.lower(), [option]):
                if line not in seen:
                    seen.add(line)
                    points.append(line)
    else:
        # Todavía no se revisó la plantilla oficial de este rubro -
        # se usa el texto de la opción tal cual, como antes.
        points = selected_options

    points.extend(split_lines(data.get("otros_revision")))

    return points


def build_blocks(data, rubrics):
    """Build replacement blocks for Excel template with data from item and rubrics."""

    code = rubric_code(
        data.get("rubro")
    )

    spec = build_template_points(data)

    programacion = build_programacion(
        data.get(
            "subitems",
            []
        )
    )

    print("SPEC =", spec)
    print("IMMUTABLE =", IMMUTABLE_POINTS)

    blocks = {

        "{{PROGRAMACION}}":
        "\n".join([
            " | ".join([
                r["area"],
                r["inicio"],
                r["fin"],
                r["obs"],
            ])
            for r in programacion
        ]),

        "__PROGRAMACION_ROWS__":
        programacion,

        "{{TRABAJOS_PREVIOS}}":
        split_lines(
            data.get(
                "trabajos_previos"
            )
        ),

        "{{SERVICIOS_BASICOS}}":
        build_services(data),

        "{{PUNTOS_REVISION}}":
        spec + IMMUTABLE_POINTS,
    }

    blocks.update(
        build_multas(data)
    )

    blocks.update(
        build_puntos_generales(data)
    )

    blocks.update(
        build_planos(data)
    )

    return blocks
    

def parse_multi(value):

    return {
        x.strip().lower()
        for x in (value or "").split(",")
        if x.strip()
    }


def build_multas(data):
    """Resolve which multas apply.

    Orden/Seguridad/Reporteria: from the MULTAS_COLUMN_ID checkbox
    selection - a selected one renders as its typed monto (a plain number
    the Lider enters in its own "Multa por ..." field) formatted with
    that multa's unit, e.g. "30" becomes "Q.30 POR EVENTO". Falls back to
    the original template's fixed default if selected but left blank.
    Anything not selected renders as "N/A".

    Atraso: independent of that checkbox - its own fixed-choice dropdown
    (N/A, .15, .30, .45, .60, .75, 1) selects the percentage directly, no
    free typing involved.
    """

    selected_options = parse_multi(data.get("multas_aplicar"))
    print("MULTAS_SELECCIONADAS =", selected_options)

    selected_keys = {
        MULTAS_OPTION_MAP[option]
        for option in selected_options
        if option in MULTAS_OPTION_MAP
    }

    def value_for(key):
        if key not in selected_keys:
            return "N/A"

        match = re.search(r"\d+(?:\.\d+)?", data.get(MULTAS_MONTO_FIELDS[key]) or "")

        if match:
            return MULTAS_FORMAT[key].format(monto=match.group())

        return MULTAS_DEFAULTS[key]

    atraso_pct = (data.get("multa_atraso_pct") or "").strip()
    atraso_value = (
        f"{atraso_pct}% POR DIA"
        if atraso_pct and atraso_pct.upper() != "N/A"
        else "N/A"
    )

    return {
        "{{MULTA_ATRASO}}": atraso_value,
        "{{MULTA_ORDEN}}": value_for("orden"),
        "{{MULTA_SEGURIDAD}}": value_for("seguridad"),
        "{{MULTA_REPORTERIA}}": value_for("reporteria"),
    }


def build_puntos_generales(data):

    selected = parse_multi(
        data.get("puntos_generales")
    )
    print("SELECTED_PUNTOS =", selected)

    return {

        "{{PG_BITACORA}}":
            "SI" if "llevar bitácora diaria" in selected else "NO",

        "{{PG_SEGURIDAD}}":
            "SI" if "encargado de seguridad industrial" in selected else "NO",

        "{{PG_PROTOCOLO}}":
            "SI" if "protocolo de seguridad" in selected else "NO",

        "{{PG_REUNION}}":
            "SI" if "reunión semanal con lider de proyecto" in selected else "NO",

        "{{PG_SUPERVISOR}}":
            "SI" if "arq / ing para supervisar" in selected else "NO",

        "{{PG_ENCARGADO}}":
        "SI"
        if any(
            "encargado técnico de supervisión" in x
            for x in selected
        )
        else "NO",
    }


def build_planos(data):

    selected = parse_multi(
        data.get("planos_entregados")
    )

    return {

        "{{PL_ARQ}}":
            "SI" if "arquitectura" in selected else "NO",

        "{{PL_COTAS}}":
            "SI" if "cotas" in selected else "NO",

        "{{PL_ELEV}}":
            "SI" if "elevaciones y secciones" in selected else "NO",

        "{{PL_HIDRO}}":
            "SI" if "hidrosanitarias" in selected else "NO",

        "{{PL_ELEC}}":
            "SI" if "electricidad" in selected else "NO",

        "{{PL_ACAB}}":
            "SI" if "acabados" in selected else "NO",

        "{{PL_ESTR_PRIN}}":
            "SI" if "estructura principal" in selected else "NO",

        "{{PL_ESTR_SEC}}":
            "SI" if "estructura secundaria" in selected else "NO",

        "{{PL_OBRAS}}":
            "SI" if "obras secundarias" in selected else "NO",
    }


