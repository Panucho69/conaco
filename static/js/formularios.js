// Ayudas de los formularios del sitio (registro, login, perfil, panel). Cada una se activa
// solo si la página tiene los elementos que usa.

// Botón del ojo: muestra u oculta la contraseña del mismo campo
document.querySelectorAll('.ver-clave').forEach(function (boton) {
  boton.addEventListener('click', function () {
    var input = boton.parentElement.querySelector('input');
    var visible = input.type === 'text';
    input.type = visible ? 'password' : 'text';
    boton.setAttribute('aria-label', visible ? 'Mostrar contraseña' : 'Ocultar contraseña');
    boton.querySelector('i').className = visible ? 'bi bi-eye' : 'bi bi-eye-slash';
  });
});

// Contraseña nueva (data-reglas): marca en verde los requisitos que ya cumple.
// El usuario se lee del campo indicado en data-usuario-de o del texto en data-usuario.
document.querySelectorAll('input[data-reglas]').forEach(function (clave) {
  var reglas = clave.closest('.campo').querySelectorAll('.reglas-clave li');
  var campoUsuario = clave.dataset.usuarioDe && document.getElementById(clave.dataset.usuarioDe);

  function revisar() {
    var valor = clave.value;
    var usuario = (campoUsuario ? campoUsuario.value : clave.dataset.usuario || '').trim().toLowerCase();
    var ok = {
      largo: valor.length >= 8,
      letras: valor.length > 0 && !/^\d+$/.test(valor),
      usuario: valor.length > 0 && valor.toLowerCase() !== usuario
    };
    reglas.forEach(function (li) { li.classList.toggle('cumple', ok[li.dataset.regla]); });
  }
  clave.addEventListener('input', revisar);
  if (campoUsuario) campoUsuario.addEventListener('input', revisar);
});

// Repetir contraseña (data-repite="id del campo original"): avisa si coinciden
document.querySelectorAll('input[data-repite]').forEach(function (repetir) {
  var original = document.getElementById(repetir.dataset.repite);
  var aviso = repetir.closest('.campo').querySelector('.coincide');

  function revisar() {
    if (!repetir.value) {
      aviso.textContent = '';
      aviso.className = 'coincide';
    } else if (repetir.value === original.value) {
      aviso.textContent = 'Las contraseñas coinciden.';
      aviso.className = 'coincide si';
    } else {
      aviso.textContent = 'Las contraseñas todavía no coinciden.';
      aviso.className = 'coincide no';
    }
  }
  repetir.addEventListener('input', revisar);
  original.addEventListener('input', revisar);
});

// Vista previa de imágenes: data-vista-previa apunta a una <img> (una foto)
// o a un contenedor (varias fotos, se muestran como miniaturas)
document.querySelectorAll('input[type=file][data-vista-previa]').forEach(function (input) {
  var destino = document.querySelector(input.dataset.vistaPrevia);
  var nombre = input.closest('.campo, .subir-imagen') && input.closest('.campo, .subir-imagen').querySelector('.archivo-elegido');

  input.addEventListener('change', function () {
    var archivos = Array.prototype.slice.call(input.files).filter(function (f) { return f.type.indexOf('image/') === 0; });
    if (nombre) {
      nombre.textContent = archivos.length === 0 ? '' :
        archivos.length === 1 ? archivos[0].name : archivos.length + ' imágenes elegidas';
    }
    if (!archivos.length) return;

    if (destino.tagName === 'IMG') {
      destino.src = URL.createObjectURL(archivos[0]);
      destino.hidden = false;
    } else {
      destino.innerHTML = '';
      archivos.forEach(function (archivo) {
        var img = document.createElement('img');
        img.src = URL.createObjectURL(archivo);
        img.alt = archivo.name;
        destino.appendChild(img);
      });
    }
  });
});

// Contador de caracteres para textareas con maxlength y data-contador
document.querySelectorAll('textarea[data-contador]').forEach(function (texto) {
  var contador = document.querySelector(texto.dataset.contador);
  function contar() { contador.textContent = texto.value.length + ' / ' + texto.maxLength; }
  texto.addEventListener('input', contar);
  contar();
});

// Formularios que borran algo: piden confirmación (data-confirmar="mensaje")
document.querySelectorAll('form[data-confirmar]').forEach(function (form) {
  form.addEventListener('submit', function (evento) {
    if (!window.confirm(form.dataset.confirmar)) evento.preventDefault();
  });
});
