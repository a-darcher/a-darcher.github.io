// Fetch publications from the publications folder
fetch('{{ site.baseurl }}/publications/')
    .then(response => response.text())
    .then(text => {
        // Parse the HTML content of the publications folder
        const parser = new DOMParser();
        const htmlDoc = parser.parseFromString(text, 'text/html');
        // Get all the links in the publications folder
        const links = htmlDoc.querySelectorAll('a');

        // Iterate through each link and add it to the publicationList
        const publicationList = document.getElementById('publicationList');
        links.forEach(link => {
            const listItem = document.createElement('li');
            const anchor = document.createElement('a');
            anchor.href = '{{ site.baseurl }}/publications/' + link.getAttribute('href');
            anchor.textContent = link.textContent;
            listItem.appendChild(anchor);
            publicationList.appendChild(listItem);
        });
    })
    .catch(error => console.error('Error fetching publications:', error));

