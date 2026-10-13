/* Checkout: QuickJS is linked into the same library as IL2CPP's code (Assets/Plugins/Android/QuickJS), so its few
   global functions with generic names get a prefix here (included from cutils.h, which every QuickJS file includes
   first). Everything else QuickJS exports already starts with JS_, js_ or lre_. */
#ifndef CHECKOUT_QJS_NAMES_H
#define CHECKOUT_QJS_NAMES_H
#define cr_copy checkout_qjs_cr_copy
#define cr_free checkout_qjs_cr_free
#define cr_init checkout_qjs_cr_init
#define cr_invert checkout_qjs_cr_invert
#define cr_op checkout_qjs_cr_op
#define cr_op1 checkout_qjs_cr_op1
#define cr_realloc checkout_qjs_cr_realloc
#define cr_regexp_canonicalize checkout_qjs_cr_regexp_canonicalize
#define i32toa checkout_qjs_i32toa
#define i64toa checkout_qjs_i64toa
#define i64toa_radix checkout_qjs_i64toa_radix
#define u32toa checkout_qjs_u32toa
#define u64toa checkout_qjs_u64toa
#define u64toa_radix checkout_qjs_u64toa_radix
#define unicode_general_category checkout_qjs_unicode_general_category
#define unicode_normalize checkout_qjs_unicode_normalize
#define unicode_prop checkout_qjs_unicode_prop
#define unicode_script checkout_qjs_unicode_script
#define unicode_sequence_prop checkout_qjs_unicode_sequence_prop
#endif
