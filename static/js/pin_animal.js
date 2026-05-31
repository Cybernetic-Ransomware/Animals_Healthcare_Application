const link = document.getElementById('togglePinnedButton');

if (link) {
  link.addEventListener('click', async function(event) {
    event.preventDefault();

    const animalId = link.dataset.animalId;
    const action = link.dataset.action;
    const newAction = (action === 'add') ? 'remove' : 'add';

    try {
      const body = new URLSearchParams({animal_id: animalId, action: action});
      const response = await fetch(link.href, {
          method: 'POST',
          headers: {
              'X-CSRFToken': getCookie('csrftoken'),
          },
          body: body,
      });

      if (!response.ok) {
        throw new Error('Request failed: ' + response.statusText);
      }

      link.dataset.action = newAction;
      link.innerText = (newAction === 'add') ? 'Add to Pinned' : 'Remove from Pinned';
    } catch (error) {
      console.error('Error:', error);
    }
  });
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
