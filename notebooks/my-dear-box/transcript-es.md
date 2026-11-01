# My dear box

Tidied transcript of a voice dump, in Spanish. The English draft in
`_posts/2026-11-01-my-dear-box.md` follows this order of ideas.
This file is the source, not the post.

---

¿Por qué a los humanos nos gustan tanto las cajas? Hay una razón primordial que viene desde el principio de la humanidad. Cuando el hombre empezó a desarrollar su tecnología, creamos flechas, anzuelos, estatuillas de las divinidades que teníamos, y como éramos nómades, las acarreábamos; imagino que en un principio en bolsas.

Con el tiempo, las bolsas, que también son de gran importancia y utilidad para nosotros, dieron lugar a las cajas, sobre todo en la era moderna o a partir de que pudimos hacer carpintería. Eso ha sido una constante en toda la historia de la humanidad. Tenemos cajas de todos los tipos, pero las de forma de prisma rectangular son las más populares, y pueden ir desde una simple caja de zapatos de cartón hasta un contenedor marítimo que cruza el océano durante años, o una caja fuerte.

¿Qué tiene de tan cautivante una caja? Está relacionado con que a los humanos nos gustan las cosas: nos gusta fabricar cosas, tener cosas, intercambiar cosas, regalar cosas. Y las cajas nos ayudan a organizar esas cosas. Si no tuviésemos cajas, nuestras cosas estarían probablemente en una gran habitación, que, por cierto, también es una caja. Las casas son cajas que tienen cuartos con forma de caja. Es imposible pensar en cualquier tipo de organización sin cajas, y eso te lo puede decir también Marie Kondo.

¿Y por qué nos sirve organizar? La razón está en nuestra mente finita. Así como nos gusta tener muchas cosas, nuestra mente no puede llevar registro de tantas cosas a la vez. Hay distintos estudios acerca de cuántos elementos de una lista puede retener una mente humana en un determinado momento, pero con seguridad la mayoría de las personas no puede manejar 100 cosas con agilidad, ni 300. Yo probablemente no llego ni a siete cosas que pueda recordar de una lista.

Ahí es donde nos interesan las cajas. Si tengo 100 cosas que recordar, ¿dónde están? Puedo tener 10 cajas con 10 cosas cada una, y le pongo una etiqueta a cada caja. De esa forma, mi mente puede encontrar con menos esfuerzo dónde está cada una de esas 100 cosas que puedo necesitar en un determinado momento. Esa es la gran función de las cajas.

Así es como los grandes depósitos organizan la mercadería: en pequeñas cajas, luego en contenedores más grandes, luego en pasillos, luego en depósitos enteros como galpones, y a veces en inmuebles distintos: un inmueble en una ciudad con cuatro galpones, otro en otra ciudad con siete galpones, y todo eso lo tienen que llevar en un sistema de inventario. Las compañías de logística no podrían sobrevivir sin cajas, cajitas y cajas más grandes, unas adentro de otras.

Esa es la gran ventaja de la caja, y no hay forma de ejecutar proyectos de gran envergadura sin una estructura, sin un plan acerca de cómo organizar esas cajas. Probablemente lo sepas si alguna vez tuviste que mudarte: lo que conlleva poner todas las cosas en cajas, mudarte, y luego encontrar las cosas dentro de esas cajas. Y eso es apenas la mínima expresión de un proyecto complejo; la mayor parte de los proyectos de logística involucran miles o millones de veces la complejidad de una mudanza y necesitan esquemas mucho más avanzados.

Ahora bien, este no es un blog de logística. O tal vez sí lo es, porque trabajé en logística y, sorpresa, también diseñé sistemas de logística. ¿Cómo se traslada todo esto al mundo de la arquitectura de software y el desarrollo de aplicaciones?

Nuestra mente es la misma. Es la misma mente de aquel hombre prehistórico que llevaba sus puntas de flecha y sus anzuelos en una bolsa, la misma que usamos para organizar una mudanza, y la misma con la que organizamos proyectos con miles de líneas de código. La mente es la misma, las capacidades son las mismas, las estructuras son las mismas.

En software siempre tenemos que pensar en cajas. Por eso tenemos módulos, carpetas o directorios, librerías, componentes; cada uno de ellos es una caja a la que le podemos dar un significado, y sabemos más o menos qué tiene adentro. Eso es lo que nos permite ir desde una necesidad, como "necesito encontrar mi taladro para tal cosa", hasta tener efectivamente el taladro en las manos.

En el software es lo mismo. Necesito saber dónde se registra el precio en el momento en que el usuario hace el pedido. ¿Dónde está eso? Necesito conocer una serie limitada de cajas, de 3 a 10, que serían los módulos del sistema, para poder abrir una de ellas, encontrar las otras cajas adentro y decir: "ok, lo de los precios debe estar en la caja grande de pedidos; dentro de pedidos, debe estar en el momento del booking; y dentro de booking, en la parte de precios". Abro esa caja y ahí probablemente me encuentre 3000 líneas de código que tengo que escanear. Pero tener esa estructura de cajas es lo que me permite llegar en tres saltos desde una necesidad hasta el código relevante.

Esa es la cuestión con las cajas: tenemos una mente finita, pero nos gusta tener muchas cosas. Antes nos gustaba tener estatuillas de barro; ahora nos gusta tener cosas como una interfaz que provee una abstracción sobre tres módulos distintos, uno de los cuales hace requests HTTP. La arquitectura de software consiste en encontrar las cajas para estas cosas que nos gusta tener ahora.

¿Por qué esas cajas siguen siendo importantes en la arquitectura de software, si ahora lo puede hacer la IA? Esto podría ser una rama muy larga de explicar. Es probable que la IA, algún día, no necesite las cajas. Va a llegar un día, que puede ser la semana que viene, en dos años, en dos siglos o nunca, en el que los humanos ni siquiera van a pensar en el código, y va a ser una gigantesca caja negra donde nadie mira nada. Una sola interfaz de voz a la que le decimos: "Dios de la IA, los pedidos de los clientes tier 2 tienen que reflejarse en la política de precios del año que viene", y nadie toca nada más.

Eso puede pasar o no, es posible, pero todavía no estamos ahí. La ventana de contexto de los modelos más poderosos que tenemos los consumidores y las empresas regulares es de un millón de tokens. No entra todo en una sola llamada. La capacidad de los modelos para manejar listas es increíblemente más grande que la de los humanos, que andamos entre 7 y 100 elementos, pero aun así no es infinita, y tampoco están definidas las estrategias ganadoras para lidiar con millones de líneas de código de forma universal.

Es imprescindible organizar millones de líneas de código de forma que entren en la ventana de contexto de los modelos y en la "ventana de contexto" de los humanos. La respuesta a eso es la arquitectura de software.

¿Y qué es la arquitectura de software? Encontrar, descubrir o diseñar las cajas más grandes, con las cajas medianas y con las cajas pequeñas, para guardar adentro todas esas líneas de código, de forma que los humanos puedan saber dónde está cada cosa, y de forma que la IA también pueda trabajar en partes del sistema mapeando directamente los requerimientos.

Si damos el requerimiento que mencioné, cambiar la política de precios del cliente, con un prompt de dos líneas, la IA, en lugar de tener que escanear miles de líneas de código con patrones distintos, perdiendo tiempo y eficacia y gastando dinero, puede identificar primero la caja donde se encuentra ese código, e ir y leer toda esa caja. Esa es la diferencia. Probablemente la IA pueda leer toda esa caja en cinco segundos, mientras que a nosotros nos llevaría horas o días, o tendríamos que conocerla de antemano. Pero las cajas siguen siendo relevantes para la productividad, tanto de la IA sola como del humano solo.

Y ahí viene el punto de quiebre. En estos días escucho a muchos programadores preguntarse "¿para qué voy a revisar, si la IA sabe hacer todo?", o directamente convertir su flujo de trabajo en una sucesión de prompts y PRs sin prestar atención a la arquitectura del software y sin revisar la estructura de las cajas.

Entonces, mi llamado para hoy es este: no necesitan revisar, si no quieren, lo que está dentro de las cajas. No tienen que revisar lo que está dentro de las cajas más chiquitas. Sí tienen que participar en el diseño de la estructura de las cajas, porque de esa forma pueden seguir haciendo el trabajo que les toca en los tiempos que corren: intervenir en cuestiones puntuales de importancia, articular, y también diseñar y asistir los flujos de la IA, para que la IA pueda mapear los requerimientos hacia esas cajas, sea más eficiente y más eficaz, y a la vez genere menos problemas que ustedes tengan que revisar.

Una sucesión de "envío esto, no reviso tanto y mergeo; envío esto, no reviso tanto y mergeo" lo único que produce es una gigantesca caja negra. Una caja negra generalmente se refiere a algo de lo que no sabemos qué pasa adentro: vemos lo que pasa afuera, pero no lo que pasa adentro. Por el contrario, una glass box, una caja de vidrio o transparente, es algo que entendemos completamente. Esa metodología de codear y mergear sin una estructura lo que hace es generar una gran caja negra.

Para el volumen de código que manejamos hoy, aspirar a tener una glass box no es realista. Ya no se puede cumplir con las expectativas del negocio, con el volumen que hay que desplegar, y además tener tiempo de revisar todo. Un humano puede revisar más o menos bien entre 200 y 400 líneas de código en una hora, nunca más de mil, y esos números simplemente no van con las expectativas de los tiempos que corren.

Entonces, la estrategia no es una gran black box, y tampoco es una glass box como antes. La respuesta es una glass box con pequeñas black boxes adentro. Vas a tener muchas black boxes, de 300 a 5000 líneas de código como máximo, según el umbral que quieras fijar. Esas black boxes no tenés que revisarlas, pero como interactúan entre sí, todo tiene que estar dentro de una glass box que vos sí entendés, y en la que sabés cómo se conecta cada parte con la otra.

Entonces, la respuesta absoluta y total a todas esas preguntas que la gente se hace sobre este tema es: una glass box con pequeñas black boxes adentro.

De nada, de nada, de nada.
