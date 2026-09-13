<?php
/**
 * Plugin Name: Morpher
 * Description: WordPress integration for Morpher-generated Elementor output.
 * Version: 0.4.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

$morpher_root = plugin_dir_path( __FILE__ );

require_once $morpher_root . 'includes/class-morpher-deployment.php';
require_once $morpher_root . 'includes/class-morpher-assets.php';
require_once $morpher_root . 'includes/class-morpher-admin.php';
require_once $morpher_root . 'includes/class-morpher-plugin.php';

$morpher_plugin = new Morpher_Plugin( __FILE__, $morpher_root );
$morpher_plugin->register();
