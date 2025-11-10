
// Adiciona informações de versionamento à página
document.addEventListener('DOMContentLoaded', function() {
    // Adiciona banner de versão
    const header = document.querySelector('.jumbo');
    if (header) {
        const versionBanner = document.createElement('div');
        versionBanner.className = 'version-banner';
        versionBanner.innerHTML = `
            <div class="version-info">
                <span class="version-badge">Versão: ${document.currentScript?.getAttribute('data-version') || '1.0.0'}</span>
                <span>Gerado em: ${new Date().toLocaleDateString('pt-BR')}</span>
            </div>
            <div class="version-info">
                <span class="version-badge">Schema: ${document.currentScript?.getAttribute('data-schema-version') || 'latest'}</span>
            </div>
        `;
        header.parentNode.insertBefore(versionBanner, header);
    }
    
    // Melhora visualização de deprecated
    const deprecatedElements = document.querySelectorAll('[data-deprecated="true"]');
    deprecatedElements.forEach(el => {
        el.classList.add('property-deprecated');
    });
    
    // Adiciona tooltips para versionamento
    const versionSpans = document.querySelectorAll('.version-info span');
    versionSpans.forEach(span => {
        span.style.cursor = 'help';
        span.title = 'Informações de versionamento';
    });
});
