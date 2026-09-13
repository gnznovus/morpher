( function () {
    'use strict';

    const config = window.MorpherAdmin || {};
    const root = document.getElementById( 'morpher-admin' );

    if ( ! root || ! config.ajaxUrl || ! config.nonce ) {
        return;
    }

    const tabs = Array.from( root.querySelectorAll( '.morpher-tab' ) );
    const panel = root.querySelector( '.morpher-tab-panel' );

    if ( ! tabs.length || ! panel ) {
        return;
    }

    const setActiveTab = ( tabName ) => {
        tabs.forEach( ( tab ) => {
            const active = tab.dataset.tab === tabName;
            tab.classList.toggle( 'nav-tab-active', active );
            tab.setAttribute( 'aria-selected', active ? 'true' : 'false' );
            tab.setAttribute( 'tabindex', active ? '0' : '-1' );
        } );
    };

    const loadTab = async ( tabName, updateHash = true ) => {
        setActiveTab( tabName );
        panel.classList.add( 'is-loading' );
        panel.setAttribute( 'aria-busy', 'true' );
        panel.innerHTML = '<p class="morpher-loading">Loading…</p>';

        const body = new URLSearchParams( {
            action: 'morpher_load_tab',
            nonce: config.nonce,
            tab: tabName,
        } );

        try {
            const response = await fetch( config.ajaxUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                },
                body: body.toString(),
            } );
            const payload = await response.json();

            if ( ! response.ok || ! payload.success || ! payload.data || typeof payload.data.html !== 'string' ) {
                throw new Error( 'Could not load Morpher tab.' );
            }

            panel.innerHTML = payload.data.html;
            if ( updateHash ) {
                window.history.replaceState( null, '', '#' + tabName );
            }
        } catch ( error ) {
            panel.innerHTML = '<div class="notice notice-error inline"><p>Could not load this Morpher tab. Refresh the page and try again.</p></div>';
        } finally {
            panel.classList.remove( 'is-loading' );
            panel.setAttribute( 'aria-busy', 'false' );
        }
    };

    tabs.forEach( ( tab ) => {
        tab.addEventListener( 'click', ( event ) => {
            event.preventDefault();
            loadTab( tab.dataset.tab );
        } );
    } );

    const requested = window.location.hash.replace( '#', '' );
    const initial = tabs.some( ( tab ) => tab.dataset.tab === requested ) ? requested : 'deployments';
    loadTab( initial, false );
}() );
