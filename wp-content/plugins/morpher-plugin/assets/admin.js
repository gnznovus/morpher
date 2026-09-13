( function () {
    'use strict';

    const config = window.MorpherAdmin || {};
    const root = document.getElementById( 'morpher-admin' );

    if ( ! root || ! config.ajaxUrl || ! config.nonce ) {
        return;
    }

    const tabs = Array.from( root.querySelectorAll( '.morpher-tab' ) );
    const panel = root.querySelector( '.morpher-tab-panel' );
    const notice = root.querySelector( '.morpher-ajax-notice' );

    if ( ! tabs.length || ! panel ) {
        return;
    }

    let currentSearch = '';

    const setActiveTab = ( tabName ) => {
        tabs.forEach( ( tab ) => {
            const active = tab.dataset.tab === tabName;
            tab.classList.toggle( 'nav-tab-active', active );
            tab.setAttribute( 'aria-selected', active ? 'true' : 'false' );
            tab.setAttribute( 'tabindex', active ? '0' : '-1' );
        } );
    };

    const showNotice = ( message, type = 'success' ) => {
        if ( ! notice || ! message ) {
            return;
        }

        notice.innerHTML = '<div class="notice notice-' + type + ' is-dismissible inline"><p></p></div>';
        notice.querySelector( 'p' ).textContent = message;
    };

    const ajaxRequest = async ( action, extra = {} ) => {
        const body = new URLSearchParams( {
            action,
            nonce: config.nonce,
            ...extra,
        } );

        const response = await fetch( config.ajaxUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            },
            body: body.toString(),
        } );

        const payload = await response.json();
        if ( ! response.ok || ! payload.success || ! payload.data ) {
            const message = payload && payload.data && payload.data.message
                ? payload.data.message
                : 'Morpher request failed.';
            throw new Error( message );
        }

        return payload.data;
    };

    const applySearch = () => {
        const input = panel.querySelector( '.morpher-template-search' );
        const rows = Array.from( panel.querySelectorAll( '.morpher-deployment-table tbody tr' ) );
        const count = panel.querySelector( '.morpher-search-count' );
        const empty = panel.querySelector( '.morpher-no-results' );

        if ( ! input || ! rows.length ) {
            return;
        }

        input.value = currentSearch;
        const query = currentSearch.trim().toLowerCase();
        let visible = 0;

        rows.forEach( ( row ) => {
            const haystack = ( row.dataset.morpherSearch || row.textContent || '' ).toLowerCase();
            const matches = ! query || haystack.includes( query );
            row.hidden = ! matches;
            if ( matches ) {
                visible += 1;
            }
        } );

        if ( count ) {
            count.textContent = query ? visible + ' of ' + rows.length : rows.length + ' total';
        }

        if ( empty ) {
            empty.hidden = visible !== 0;
        }
    };

    const replaceDeployments = ( data ) => {
        if ( typeof data.html === 'string' ) {
            panel.innerHTML = data.html;
        }
        applySearch();
        if ( data.message ) {
            showNotice( data.message );
        }
    };

    const setBusy = ( button, busy, busyLabel = 'Working…' ) => {
        if ( ! button ) {
            return;
        }

        if ( busy ) {
            button.dataset.label = button.textContent;
            button.textContent = busyLabel;
            button.disabled = true;
        } else {
            button.textContent = button.dataset.label || button.textContent;
            button.disabled = false;
        }
    };

    const loadTab = async ( tabName, updateHash = true ) => {
        setActiveTab( tabName );
        panel.classList.add( 'is-loading' );
        panel.setAttribute( 'aria-busy', 'true' );
        panel.innerHTML = '<p class="morpher-loading">Loading…</p>';

        try {
            const data = await ajaxRequest( 'morpher_load_tab', { tab: tabName } );
            panel.innerHTML = typeof data.html === 'string' ? data.html : '';
            if ( tabName === 'deployments' ) {
                applySearch();
            }
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

    panel.addEventListener( 'input', ( event ) => {
        if ( ! event.target.matches( '.morpher-template-search' ) ) {
            return;
        }

        currentSearch = event.target.value;
        applySearch();
    } );

    panel.addEventListener( 'click', async ( event ) => {
        const refreshDiagnostics = event.target.closest( '.morpher-refresh-diagnostics' );
        if ( refreshDiagnostics ) {
            event.preventDefault();
            loadTab( 'diagnostics', false );
            return;
        }

        const redeploy = event.target.closest( '.morpher-redeploy' );
        const redeployAll = event.target.closest( '.morpher-redeploy-all' );
        const processStaged = event.target.closest( '.morpher-process-staged' );
        const button = redeploy || redeployAll || processStaged;

        if ( ! button ) {
            return;
        }

        event.preventDefault();
        setBusy( button, true, redeploy ? 'Re-deploying…' : 'Working…' );
        panel.setAttribute( 'aria-busy', 'true' );

        try {
            let data;
            if ( redeploy ) {
                data = await ajaxRequest( 'morpher_redeploy', {
                    deployment: redeploy.dataset.deployment || '',
                } );
            } else if ( redeployAll ) {
                data = await ajaxRequest( 'morpher_redeploy_all' );
            } else {
                data = await ajaxRequest( 'morpher_process_deployments' );
            }
            replaceDeployments( data );
        } catch ( error ) {
            showNotice( error.message || 'Morpher request failed.', 'error' );
            setBusy( button, false );
        } finally {
            panel.setAttribute( 'aria-busy', 'false' );
        }
    } );

    const requested = window.location.hash.replace( '#', '' );
    const initial = tabs.some( ( tab ) => tab.dataset.tab === requested ) ? requested : 'deployments';
    loadTab( initial, false );
}() );
