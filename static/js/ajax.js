// AJAX del panel: envía los formularios con fetch() y actualiza solo la parte de la página que cambió.
//
//  <form data-ajax>      se envía sin recargar. La vista responde JSON (ver respuesta_ajax en views.py)
//                        con un mensaje y los cambios a aplicar: reemplazar, contenido, agregar, quitar, textos.
//  <form data-limpiar>   además se vacía al guardar bien (agregar categoría, cambiar contraseña).
//  <a data-modal>        abre su página dentro de la ventana #modal-ajax en lugar de cambiar de página.
//
// Si el navegador no tiene JavaScript, los mismos formularios funcionan con una recarga normal.
(function () {
  var CABECERAS = { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' };

  // ---------- Avisos flotantes ----------
  function avisar(texto, ok) {
    if (!texto) return;
    var zona = document.getElementById('avisos');
    if (!zona) {
      zona = document.createElement('div');
      zona.id = 'avisos';
      zona.className = 'avisos';
      zona.setAttribute('aria-live', 'polite');
      document.body.appendChild(zona);
    }
    var aviso = document.createElement('div');
    aviso.className = 'aviso ' + (ok ? 'aviso-ok' : 'aviso-error');
    aviso.setAttribute('role', ok ? 'status' : 'alert');
    aviso.innerHTML = '<i class="bi ' + (ok ? 'bi-check-circle' : 'bi-exclamation-circle') + '" aria-hidden="true"></i>';
    aviso.appendChild(document.createTextNode(' ' + texto));
    zona.appendChild(aviso);
    setTimeout(function () {
      aviso.classList.add('saliendo');
      setTimeout(function () { aviso.remove(); }, 300);
    }, ok ? 3500 : 6000);
  }

  // ---------- Aplicar los cambios que manda el servidor ----------
  function aHtml(texto) {
    var plantilla = document.createElement('template');
    plantilla.innerHTML = texto.trim();
    return plantilla.content;
  }

  function resaltar(elemento) {
    if (!elemento || !elemento.classList) return;
    elemento.classList.add('recien-cambiado');
    setTimeout(function () { elemento.classList.remove('recien-cambiado'); }, 1600);
  }

  function aplicar(datos) {
    Object.entries(datos.reemplazar || {}).forEach(function (par) {
      var viejo = document.querySelector(par[0]);
      if (!viejo) return;
      var nuevo = aHtml(par[1]).firstElementChild;
      viejo.replaceWith(nuevo);
      Canaco.iniciar(nuevo);
      if (nuevo.tagName === 'TR' || nuevo.tagName === 'ARTICLE') resaltar(nuevo);
    });
    (datos.quitar || []).forEach(function (selector) {
      var elemento = document.querySelector(selector);
      if (!elemento) return;
      elemento.classList.add('saliendo');
      setTimeout(function () { elemento.remove(); }, 250);
    });
    Object.entries(datos.contenido || {}).forEach(function (par) {
      var caja = document.querySelector(par[0]);
      if (!caja) return;
      setTimeout(function () {  // después de que termine de salir lo que se quitó
        caja.innerHTML = par[1];
        Canaco.iniciar(caja);
      }, 260);
    });
    Object.entries(datos.agregar || {}).forEach(function (par) {
      var caja = document.querySelector(par[0]);
      if (!caja) return;
      var nuevo = aHtml(par[1]).firstElementChild;
      caja.appendChild(nuevo);
      Canaco.iniciar(nuevo);
      resaltar(nuevo);
    });
    Object.entries(datos.textos || {}).forEach(function (par) {
      document.querySelectorAll(par[0]).forEach(function (el) { el.textContent = par[1]; });
    });
  }

  // ---------- Errores en el formulario ----------
  function limpiarErrores(form) {
    form.querySelectorAll('.campo-error').forEach(function (el) { el.classList.remove('campo-error'); });
    var alerta = form.querySelector('.alerta-form');
    if (alerta) alerta.remove();
  }

  function marcarError(form, datos) {
    var campo = datos.campo && form.querySelector('[name="' + datos.campo + '"]');
    var dentroDeModal = form.closest('.modal');
    if (campo) {
      (campo.closest('.campo, fieldset, .foto-editable') || campo).classList.add('campo-error');
      campo.focus();
    }
    // En la ventana modal el error se ve dentro del formulario; en la página, como aviso flotante
    if (dentroDeModal || form.classList.contains('acceso-form')) {
      var alerta = document.createElement('div');
      alerta.className = 'alert alert-danger alerta-form';
      alerta.setAttribute('role', 'alert');
      alerta.textContent = datos.mensaje;
      form.prepend(alerta);
    } else {
      avisar(datos.mensaje, false);
    }
  }

  // ---------- Enviar un formulario ----------
  async function enviar(form) {
    var boton = form.querySelector('[type=submit]');
    form.classList.add('enviando');
    form.setAttribute('aria-busy', 'true');
    if (boton) boton.disabled = true;
    limpiarErrores(form);

    try {
      var respuesta = await fetch(form.action || location.href, {
        method: 'POST',
        body: new FormData(form),
        headers: CABECERAS,
        credentials: 'same-origin'
      });
      var tipo = respuesta.headers.get('content-type') || '';
      if (!tipo.includes('application/json')) {
        // La sesión expiró o el servidor contestó con una página: se abre normalmente
        location.href = respuesta.url;
        return;
      }
      var datos = await respuesta.json();

      if (!datos.ok) {
        marcarError(form, datos);
        return;
      }
      if (form.hasAttribute('data-limpiar')) {
        form.reset();
        form.querySelectorAll('input').forEach(function (i) { i.dispatchEvent(new Event('input')); });
      }
      form.querySelectorAll('input[type=file]').forEach(function (i) { i.value = ''; });
      if (datos.cerrar_modal) cerrarModal();
      aplicar(datos);
      avisar(datos.mensaje, true);
    } catch (error) {
      avisar('No se pudo conectar con el servidor. Revisa tu internet e inténtalo de nuevo.', false);
    } finally {
      form.classList.remove('enviando');
      form.removeAttribute('aria-busy');
      if (boton && boton.isConnected) boton.disabled = false;
    }
  }

  document.addEventListener('submit', function (evento) {
    var form = evento.target.closest('form[data-ajax]');
    if (!form || evento.defaultPrevented) return;
    evento.preventDefault();
    if (form.classList.contains('enviando')) return;  // evita envíos dobles
    enviar(form);
  });

  // ---------- Ventana modal ----------
  function modal() {
    var elemento = document.getElementById('modal-ajax');
    return elemento && bootstrap.Modal.getOrCreateInstance(elemento);
  }

  function cerrarModal() {
    var m = modal();
    if (m) m.hide();
  }

  document.addEventListener('click', async function (evento) {
    var enlace = evento.target.closest('a[data-modal]');
    if (!enlace || !modal() || evento.ctrlKey || evento.metaKey) return;
    evento.preventDefault();

    try {
      var respuesta = await fetch(enlace.href, { headers: CABECERAS, credentials: 'same-origin' });
      var tipo = respuesta.headers.get('content-type') || '';
      if (!tipo.includes('application/json')) { location.href = enlace.href; return; }
      var datos = await respuesta.json();
      if (!datos.html) { avisar(datos.mensaje, false); return; }

      var elemento = document.getElementById('modal-ajax');
      elemento.querySelector('.modal-title').textContent = datos.titulo || '';
      var cuerpo = elemento.querySelector('.modal-body');
      cuerpo.innerHTML = datos.html;
      Canaco.iniciar(cuerpo);
      modal().show();
    } catch (error) {
      location.href = enlace.href;
    }
  });

  // Al abrirse, enfoca el primer campo; al cerrarse, vacía el contenido
  document.addEventListener('shown.bs.modal', function (evento) {
    if (evento.target.id !== 'modal-ajax') return;
    var primero = evento.target.querySelector('.modal-body input:not([type=hidden]), .modal-body select');
    if (primero) primero.focus();
  });
  document.addEventListener('hidden.bs.modal', function (evento) {
    if (evento.target.id === 'modal-ajax') evento.target.querySelector('.modal-body').innerHTML = '';
  });
})();
