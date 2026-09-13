<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Diagnostics {
    private $deployments;
    private $root;

    public function __construct( Morpher_Deployment $deployments, $root ) {
        $this->deployments = $deployments;
        $this->root        = untrailingslashit( $root );
    }

    public function system_checks() {
        $uploads = wp_upload_dir();
        $upload_ok = empty( $uploads['error'] ) && ! empty( $uploads['basedir'] ) && wp_is_writable( $uploads['basedir'] );

        $asset_path = empty( $uploads['basedir'] )
            ? ''
            : trailingslashit( $uploads['basedir'] ) . 'morpher-assets';
        $asset_parent = $asset_path && is_dir( $asset_path ) ? $asset_path : ( isset( $uploads['basedir'] ) ? $uploads['basedir'] : '' );
        $asset_ok = $asset_parent && wp_is_writable( $asset_parent );

        $deployment_root = trailingslashit( $this->root ) . 'deployments';
        $deployment_ok = is_dir( $deployment_root ) && is_readable( $deployment_root ) && wp_is_writable( $deployment_root );

        $php_ok = version_compare( PHP_VERSION, '8.0', '>=' );

        return array(
            $this->check( 'WordPress', true, 'WordPress ' . get_bloginfo( 'version' ) ),
            $this->check( 'Elementor', $this->elementor_ready(), $this->elementor_detail() ),
            $this->check( 'PHP', $php_ok, 'PHP ' . PHP_VERSION . ( $php_ok ? '' : ' — Morpher requires PHP 8.0+' ) ),
            $this->check( 'Uploads', $upload_ok, $upload_ok ? 'Writable' : $this->upload_error( $uploads ) ),
            $this->check( 'Morpher Assets', $asset_ok, $asset_ok ? 'Writable' : 'Asset destination is not writable.' ),
            $this->check( 'Deployments', $deployment_ok, $deployment_ok ? 'Readable and writable' : 'Deployment directory is unavailable or not writable.' ),
        );
    }

    public function integration_checks() {
        return array(
            $this->check( 'Elementor Integration', $this->elementor_ready(), $this->elementor_ready() ? 'Ready' : 'Elementor runtime is unavailable.' ),
            $this->check( 'AJAX API', true, 'Ready — this diagnostics response was loaded through admin AJAX.' ),
            $this->check( 'REST API', null, 'Not configured yet.' ),
            $this->check( 'Morpher Listener', null, 'Not configured yet.' ),
        );
    }

    public function recent_issues() {
        $issues = array();

        foreach ( $this->deployments->rows() as $row ) {
            if ( 'failed' !== $row['status'] ) {
                continue;
            }

            $issues[] = array(
                'title'   => $row['title'],
                'slug'    => $row['slug'],
                'message' => $row['error'] ? $row['error'] : 'Deployment failed without an error message.',
            );
        }

        return $issues;
    }

    private function check( $label, $healthy, $detail ) {
        return array(
            'label'   => $label,
            'status'  => null === $healthy ? 'neutral' : ( $healthy ? 'healthy' : 'error' ),
            'detail'  => $detail,
        );
    }

    private function elementor_ready() {
        return defined( 'ELEMENTOR_VERSION' ) && class_exists( '\\Elementor\\Plugin' );
    }

    private function elementor_detail() {
        if ( ! $this->elementor_ready() ) {
            return 'Elementor is not active or its runtime is unavailable.';
        }

        return 'Elementor ' . ELEMENTOR_VERSION;
    }

    private function upload_error( $uploads ) {
        if ( ! empty( $uploads['error'] ) ) {
            return (string) $uploads['error'];
        }

        return 'Upload directory is not writable.';
    }
}
