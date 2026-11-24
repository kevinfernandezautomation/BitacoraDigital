const toggle = document.querySelector('#toggle-password');
const password = document.querySelector('#id_password');
if (toggle && password) {
  toggle.hidden = false;
  toggle.addEventListener('click', () => {
    const visible = password.type === 'password';
    password.type = visible ? 'text' : 'password';
    toggle.textContent = visible ? 'Ocultar' : 'Mostrar';
    toggle.setAttribute('aria-pressed', String(visible));
  });
}
